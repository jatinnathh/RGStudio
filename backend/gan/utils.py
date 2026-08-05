# backend/gan/utils.py
#
# Image utility functions for the GAN generation module.
# Handles: URL downloading, PIL ↔ tensor conversion, base64 encoding, temp files.

import base64
import io
import os

import requests
import torch
from PIL import Image
from torchvision import transforms

from gan.config import get_gan_settings
from rag.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_gan_settings()

# ── Transforms ────────────────────────────────────────────────────────────

_to_tensor = transforms.ToTensor()  # PIL → [0, 1] tensor
_to_pil = transforms.ToPILImage()   # tensor → PIL


def pil_to_tensor(image: Image.Image, size: int | None = None) -> torch.Tensor:
    """
    Convert PIL image to [1, 3, H, W] float tensor in [0, 1] range.
    Optionally resize to `size x size`.
    """
    image = image.convert("RGB")

    if size is not None:
        image = image.resize((size, size), Image.LANCZOS)

    tensor = _to_tensor(image).unsqueeze(0)  # [1, 3, H, W]
    return tensor


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """
    Convert [1, 3, H, W] or [3, H, W] tensor to PIL image.
    Clamps values to [0, 1] to avoid artifacts.
    """
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)

    tensor = tensor.clamp(0, 1).cpu()
    return _to_pil(tensor)


# ── Image Loading ─────────────────────────────────────────────────────────

def load_image_from_url(url: str, max_bytes: int = 10 * 1024 * 1024) -> Image.Image:
    """
    Download or load an image from URL or local /images/ path, returning a PIL Image.
    Caps image dimensions to avoid OOM.
    """
    from pathlib import Path

    if url.startswith("/images/"):
        relative = url.replace("/images/", "")
        backend_dir = Path(__file__).resolve().parent.parent
        local_file = backend_dir / "art_dataset" / relative
        if local_file.exists():
            logger.debug(f"Loading local reference image from disk: {local_file}")
            image = Image.open(local_file).convert("RGB")
            max_dim = settings.MAX_IMAGE_SIZE
            if max(image.size) > max_dim:
                image.thumbnail((max_dim, max_dim), Image.LANCZOS)
            return image
        else:
            logger.warning(f"Local image file not found at {local_file}")

    logger.debug(f"Downloading image from: {url[:80]}...")

    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
        stream=True,
    )
    response.raise_for_status()

    content = b""
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > max_bytes:
            raise ValueError(f"Image too large (>{max_bytes / 1e6:.0f}MB)")

    image = Image.open(io.BytesIO(content)).convert("RGB")

    # Cap dimensions to avoid OOM
    max_dim = settings.MAX_IMAGE_SIZE
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.LANCZOS)

    logger.debug(f"Loaded image: {image.size}")
    return image


def load_image_from_bytes(data: bytes) -> Image.Image:
    """Load a PIL image from raw bytes (e.g. from file upload)."""
    image = Image.open(io.BytesIO(data)).convert("RGB")

    max_dim = settings.MAX_IMAGE_SIZE
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.LANCZOS)

    return image


# ── Image Saving ──────────────────────────────────────────────────────────

def pil_to_base64(image: Image.Image, quality: int | None = None) -> str:
    """Encode a PIL image to base64 JPEG string."""
    quality = quality or settings.JPEG_QUALITY

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def ensure_temp_dir() -> str:
    """Create and return the temp directory for generated images."""
    temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # backend/
        settings.TEMP_DIR,
    )
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
