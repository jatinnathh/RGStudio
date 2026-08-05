# backend/gan/models/vgg_encoder.py
#
# VGG19 feature extractor for AdaIN style transfer.
# Extracts intermediate features at specific relu layers.
# Pretrained on ImageNet — weights auto-downloaded (~80MB, cached).

from functools import lru_cache

import torch
from torch import nn
from torchvision.models import VGG19_Weights, vgg19

from rag.utils.logger import get_logger

logger = get_logger(__name__)

# VGG19 layer name → index mapping (after each ReLU activation)
VGG_LAYER_MAP = {
    "relu1_1": 1,
    "relu1_2": 3,
    "relu2_1": 6,
    "relu2_2": 8,
    "relu3_1": 11,
    "relu3_2": 13,
    "relu3_3": 15,
    "relu3_4": 17,
    "relu4_1": 20,
    "relu4_2": 22,
    "relu4_3": 24,
    "relu4_4": 26,
}

# ImageNet normalization constants
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


class VGGEncoder(nn.Module):
    """
    VGG19 feature extractor that returns intermediate activations.
    Used for both content and style feature extraction in AdaIN.
    
    The network is frozen (no gradients) — we only use it for inference.
    """

    def __init__(self, device: str = "cpu"):
        super().__init__()
        self.device = device

        # Load pretrained VGG19 and extract only the feature layers
        vgg = vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features.eval()

        # We only need up to relu4_1 (index 20) for AdaIN
        self.layers = nn.Sequential(*list(vgg.children())[:21])

        # Freeze all parameters
        for param in self.parameters():
            param.requires_grad = False

        self.to(device)

        # Pre-compute normalization tensors on target device
        self._mean = IMAGENET_MEAN.to(device)
        self._std = IMAGENET_STD.to(device)

        logger.info(f"VGG19 encoder loaded on {device} (up to relu4_1)")

    def _normalize(self, x: torch.Tensor) -> torch.Tensor:
        """Apply ImageNet normalization to input tensor [B, 3, H, W] in range [0, 1]."""
        return (x - self._mean) / self._std

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract relu4_1 features (the content/style representation).
        
        Args:
            x: Input tensor [B, 3, H, W], values in [0, 1].
            
        Returns:
            Features at relu4_1: [B, 512, H/8, W/8]
        """
        x = self._normalize(x)
        return self.layers(x)

    def extract_multi_scale(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        Extract features at multiple VGG layers (for style loss computation).
        
        Returns:
            Dict mapping layer name -> feature tensor.
            Keys: relu1_1, relu2_1, relu3_1, relu4_1
        """
        x = self._normalize(x)
        features = {}
        style_layers = {"relu1_1": 1, "relu2_1": 6, "relu3_1": 11, "relu4_1": 20}

        for i, layer in enumerate(self.layers):
            x = layer(x)
            for name, idx in style_layers.items():
                if i == idx:
                    features[name] = x

        return features


@lru_cache(maxsize=1)
def get_encoder(device: str = "cpu") -> VGGEncoder:
    """Get or create cached VGG encoder instance."""
    logger.info("Initializing VGG19 encoder (first call downloads ~80MB weights)...")
    return VGGEncoder(device=device)
