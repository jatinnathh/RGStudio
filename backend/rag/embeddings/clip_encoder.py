# backend/rag/embeddings/clip_encoder.py

import clip
import torch
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from functools import lru_cache

from rag.config import get_settings
from rag.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Load CLIP once and cache. Thread-safe via lru_cache."""
    logger.info(f"Loading CLIP model: {settings.CLIP_MODEL} on {settings.CLIP_DEVICE}")
    model, preprocess = clip.load(settings.CLIP_MODEL, device=settings.CLIP_DEVICE)
    model.eval()
    return model, preprocess


def encode_text(query: str) -> list[float]:
    """
    Encode a text query into a normalized CLIP embedding.
    Returns a flat list of floats (length 512 for ViT-B/32).
    """
    model, _ = _load_model()
    device = settings.CLIP_DEVICE

    with torch.no_grad():
        tokens = clip.tokenize([query], truncate=True).to(device)
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # L2 normalize

    logger.debug(f"Encoded text query — shape: {embedding.shape}")
    return embedding.squeeze().cpu().numpy().tolist()


def encode_image_from_url(image_url: str) -> list[float]:
    model, preprocess = _load_model()
    device = settings.CLIP_DEVICE

    # Stream response, cap at 10MB
    response = requests.get(
        image_url,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
        stream=True
    )
    response.raise_for_status()

    # Read max 10MB
    MAX_BYTES = 10 * 1024 * 1024
    content = b""
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_BYTES:
            raise ValueError(f"Image too large (>{MAX_BYTES/1e6:.0f}MB), use a smaller image URL")

    image = Image.open(BytesIO(content)).convert("RGB")
    image.thumbnail((512, 512))  # CLIP only needs 224px anyway

    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    logger.debug(f"Encoded image from URL — shape: {embedding.shape}")
    return embedding.squeeze().cpu().numpy().tolist()


def encode_image_from_pil(image: Image.Image) -> list[float]:
    """
    Encode an already-loaded PIL image. Useful during ingestion.
    """
    model, preprocess = _load_model()
    device = settings.CLIP_DEVICE
    image.thumbnail((1024, 1024))  # add this line

    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze().cpu().numpy().tolist()