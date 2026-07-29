# backend/gan/style_transfer.py
#
# Core AdaIN (Adaptive Instance Normalization) style transfer engine.
#
# Based on: "Arbitrary Style Transfer in Real-time with Adaptive Instance
# Normalization" — Huang & Belongie, 2017.
#
# Pipeline:
#   1. Encode content image → VGG19 relu4_1 features
#   2. Encode style image   → VGG19 relu4_1 features
#   3. AdaIN: align content feature statistics (mean/std) to style's
#   4. Decode aligned features → output image via pretrained decoder
#
# Single forward pass — ~2-5 seconds on CPU, <1s on GPU.

import torch
from PIL import Image

from gan.config import get_gan_settings
from gan.models.vgg_encoder import get_encoder
from gan.models.decoder import get_decoder
from gan.utils import pil_to_tensor, tensor_to_pil
from rag.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_gan_settings()


def adaptive_instance_normalization(
    content_feat: torch.Tensor,
    style_feat: torch.Tensor,
) -> torch.Tensor:
    """
    Adaptive Instance Normalization (AdaIN).

    Aligns the channel-wise mean and std of content features to match
    those of style features.

    Args:
        content_feat: [B, C, H, W] content features from VGG encoder.
        style_feat:   [B, C, H, W] style features from VGG encoder.

    Returns:
        Normalized features [B, C, H, W] with style's statistics.
    """
    # Compute per-channel mean and std (over spatial dims H, W)
    content_mean = content_feat.mean(dim=[2, 3], keepdim=True)
    content_std = content_feat.std(dim=[2, 3], keepdim=True) + 1e-6

    style_mean = style_feat.mean(dim=[2, 3], keepdim=True)
    style_std = style_feat.std(dim=[2, 3], keepdim=True) + 1e-6

    # Normalize content → zero mean, unit std → re-scale with style stats
    normalized = (content_feat - content_mean) / content_std
    return normalized * style_std + style_mean


def style_transfer(
    content_image: Image.Image,
    style_image: Image.Image,
    alpha: float | None = None,
    output_size: int | None = None,
) -> Image.Image:
    """
    Perform AdaIN style transfer.

    Args:
        content_image: PIL image to apply style to.
        style_image:   PIL image whose style to transfer.
        alpha:         Style strength (0.0 = pure content, 1.0 = pure style).
                       Defaults to GANSettings.STYLE_WEIGHT.
        output_size:   Output resolution (square). Defaults to GANSettings.OUTPUT_SIZE.

    Returns:
        PIL image with the content of `content_image` rendered in the style
        of `style_image`.
    """
    alpha = alpha if alpha is not None else settings.STYLE_WEIGHT
    output_size = output_size or settings.OUTPUT_SIZE
    device = settings.GAN_DEVICE

    logger.info(
        f"Style transfer: alpha={alpha:.2f}, output_size={output_size}, "
        f"device={device}"
    )

    # Load models (cached singletons)
    encoder = get_encoder(device)
    decoder = get_decoder(device)

    # Convert PIL → tensors, resize to output_size
    content_tensor = pil_to_tensor(content_image, size=output_size).to(device)
    style_tensor = pil_to_tensor(style_image, size=output_size).to(device)

    with torch.no_grad():
        # 1. Encode both through VGG19 → relu4_1 features
        content_features = encoder(content_tensor)
        style_features = encoder(style_tensor)

        # 2. AdaIN: align content features to style statistics
        adain_features = adaptive_instance_normalization(
            content_features, style_features
        )

        # 3. Blend: interpolate between content features and stylized features
        #    alpha=0 → content, alpha=1 → full style
        blended = alpha * adain_features + (1 - alpha) * content_features

        # 4. Decode back to image
        output_tensor = decoder(blended)

    # Convert tensor → PIL
    result = tensor_to_pil(output_tensor)

    logger.info(f"Style transfer complete → {result.size}")
    return result


def multi_style_transfer(
    content_image: Image.Image,
    style_images: list[Image.Image],
    weights: list[float] | None = None,
    alpha: float | None = None,
    output_size: int | None = None,
) -> Image.Image:
    """
    Multi-style transfer: blend features from multiple style images.

    Useful when RAG returns several reference artworks — their styles
    can be averaged for a richer output.

    Args:
        content_image: Content source.
        style_images:  List of style source images.
        weights:       Per-style weights (normalized internally). Defaults to equal.
        alpha:         Overall style strength.
        output_size:   Output resolution.

    Returns:
        Stylized PIL image blending multiple style references.
    """
    if not style_images:
        raise ValueError("Need at least one style image")

    if len(style_images) == 1:
        return style_transfer(content_image, style_images[0], alpha, output_size)

    alpha = alpha if alpha is not None else settings.STYLE_WEIGHT
    output_size = output_size or settings.OUTPUT_SIZE
    device = settings.GAN_DEVICE

    # Normalize weights
    if weights is None:
        weights = [1.0 / len(style_images)] * len(style_images)
    else:
        total = sum(weights)
        weights = [w / total for w in weights]

    encoder = get_encoder(device)
    decoder = get_decoder(device)

    content_tensor = pil_to_tensor(content_image, size=output_size).to(device)

    with torch.no_grad():
        content_features = encoder(content_tensor)

        # Weighted average of style features
        blended_style = torch.zeros_like(content_features)
        for img, weight in zip(style_images, weights):
            style_tensor = pil_to_tensor(img, size=output_size).to(device)
            style_features = encoder(style_tensor)
            adain_features = adaptive_instance_normalization(
                content_features, style_features
            )
            blended_style += weight * adain_features

        # Apply alpha blending
        blended = alpha * blended_style + (1 - alpha) * content_features

        output_tensor = decoder(blended)

    result = tensor_to_pil(output_tensor)
    logger.info(f"Multi-style transfer ({len(style_images)} styles) → {result.size}")
    return result
