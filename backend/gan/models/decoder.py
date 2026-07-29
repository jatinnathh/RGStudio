# backend/gan/models/decoder.py
#
# AdaIN decoder — mirrors VGG19 encoder in reverse.
# Takes AdaIN-normalized features at relu4_1 and reconstructs the image.
#
# Architecture: Nearest-neighbor upsampling + reflection padding + conv layers.
# This avoids checkerboard artifacts that plague transposed convolutions.

import torch
import torch.nn as nn
from functools import lru_cache
from rag.utils.logger import get_logger

logger = get_logger(__name__)


class AdaINDecoder(nn.Module):
    """
    Decoder network that inverts VGG19 features back to an image.
    
    Architecture mirrors VGG19 encoder (relu4_1 → image) in reverse:
      relu4_1 (512ch) → relu3_1 (256ch) → relu2_1 (128ch) → relu1_1 (64ch) → RGB (3ch)
    
    Uses:
      - Nearest-neighbor upsampling (no learnable upsample = no checkerboard)
      - Reflection padding (better than zero-pad for artistic images)
      - ReLU activations between conv layers
    """

    def __init__(self):
        super().__init__()

        self.network = nn.Sequential(
            # From relu4_1: [B, 512, H/8, W/8]
            nn.ReflectionPad2d(1),
            nn.Conv2d(512, 256, 3),
            nn.ReLU(inplace=True),

            nn.Upsample(scale_factor=2, mode="nearest"),  # → H/4

            nn.ReflectionPad2d(1),
            nn.Conv2d(256, 256, 3),
            nn.ReLU(inplace=True),

            nn.ReflectionPad2d(1),
            nn.Conv2d(256, 256, 3),
            nn.ReLU(inplace=True),

            nn.ReflectionPad2d(1),
            nn.Conv2d(256, 256, 3),
            nn.ReLU(inplace=True),

            nn.ReflectionPad2d(1),
            nn.Conv2d(256, 128, 3),
            nn.ReLU(inplace=True),

            nn.Upsample(scale_factor=2, mode="nearest"),  # → H/2

            nn.ReflectionPad2d(1),
            nn.Conv2d(128, 128, 3),
            nn.ReLU(inplace=True),

            nn.ReflectionPad2d(1),
            nn.Conv2d(128, 64, 3),
            nn.ReLU(inplace=True),

            nn.Upsample(scale_factor=2, mode="nearest"),  # → H

            nn.ReflectionPad2d(1),
            nn.Conv2d(64, 64, 3),
            nn.ReLU(inplace=True),

            nn.ReflectionPad2d(1),
            nn.Conv2d(64, 3, 3),  # Final output: 3 channels (RGB)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Decode VGG features back to an image.
        
        Args:
            x: Feature tensor from AdaIN [B, 512, H/8, W/8]
            
        Returns:
            Reconstructed image [B, 3, H, W] with values in ~[0, 1]
        """
        return self.network(x)


# Pre-trained decoder weights URL (trained to invert VGG19 features)
# This is the standard AdaIN decoder from Huang & Belongie (2017)
DECODER_WEIGHTS_URL = "https://huggingface.co/merve/adain-style-transfer/resolve/main/decoder.pth"


@lru_cache(maxsize=1)
def get_decoder(device: str = "cpu") -> AdaINDecoder:
    """
    Get or create cached AdaIN decoder.
    
    Attempts to load pretrained weights from HuggingFace.
    Falls back to random initialization if download fails
    (results will be lower quality but still functional).
    """
    decoder = AdaINDecoder()

    try:
        import requests
        from io import BytesIO

        logger.info("Downloading pretrained AdaIN decoder weights from HuggingFace...")
        response = requests.get(DECODER_WEIGHTS_URL, timeout=30)
        response.raise_for_status()

        state_dict = torch.load(
            BytesIO(response.content),
            map_location=device,
            weights_only=True,
        )

        # The pretrained weights may use different key naming.
        # Try direct load first, then try with key mapping.
        try:
            decoder.load_state_dict(state_dict)
            logger.info("Loaded pretrained decoder weights (direct match)")
        except RuntimeError:
            # Map keys: some checkpoints use flat numbering
            new_state = {}
            decoder_keys = list(decoder.state_dict().keys())
            weight_keys = list(state_dict.keys())

            if len(decoder_keys) == len(weight_keys):
                for dk, wk in zip(decoder_keys, weight_keys):
                    new_state[dk] = state_dict[wk]
                decoder.load_state_dict(new_state)
                logger.info("Loaded pretrained decoder weights (remapped keys)")
            else:
                logger.warning(
                    f"Key count mismatch: decoder={len(decoder_keys)}, "
                    f"weights={len(weight_keys)}. Using random init."
                )

    except Exception as e:
        logger.warning(f"Could not load pretrained decoder: {e}. Using random init.")

    decoder = decoder.eval().to(device)

    # Freeze decoder for inference
    for param in decoder.parameters():
        param.requires_grad = False

    return decoder
