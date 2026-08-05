# backend/gan/generate.py
#
# Main generation orchestrator — the entry point for all art generation.
#
# Two modes:
#   Mode 1: Text → Art  (text_to_art)
#     User query → RAG pipeline → CLIP ranker picks best reference
#     → download reference as style source → AdaIN style transfer → output
#
#   Mode 2: Image + Style → Styled Image  (style_transfer_from_upload)
#     User uploads image + describes target style → RAG retrieves references
#     → CLIP ranker picks best match → AdaIN(upload, reference) → output
#
# Both modes return a GenerationResult with the image + metadata.

import time
from dataclasses import dataclass

from PIL import Image

from gan.clip_ranker import pick_best_reference, score_output
from gan.config import get_gan_settings
from gan.style_transfer import multi_style_transfer, style_transfer
from gan.utils import load_image_from_url, pil_to_base64
from rag.pipeline import run_rag_pipeline
from rag.schemas.models import PipelineRequest, RetrievedArtwork
from rag.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_gan_settings()


@dataclass
class GenerationResult:
    """Result of a generation operation."""
    image: Image.Image          # The generated/stylized PIL image
    image_base64: str           # Base64-encoded JPEG
    style_reference: RetrievedArtwork | None  # Which artwork was used as style
    clip_score: float           # CLIP similarity between output and query
    generation_time_ms: int     # Wall-clock generation time
    query: str                  # Original query
    message: str                # Human-readable status message


def text_to_art(
    query: str,
    top_k: int = 5,
    style_weight: float | None = None,
    output_size: int | None = None,
    use_multi_style: bool = False,
    num_style_refs: int = 3,
) -> GenerationResult:
    """
    Text → Art generation pipeline.

    1. Run RAG pipeline to retrieve style references for the query
    2. CLIP ranker picks the best reference artwork
    3. Download the reference image
    4. Create a content seed (gradient noise or the reference itself)
    5. Apply AdaIN style transfer
    6. Score output with CLIP

    Args:
        query:           Natural language style description.
        top_k:           Number of references to retrieve from RAG.
        style_weight:    Style strength (0.0 - 1.0). Defaults to config.
        output_size:     Output resolution (square). Defaults to config.
        use_multi_style: If True, blend multiple style references.
        num_style_refs:  Number of style references to blend (if multi_style).

    Returns:
        GenerationResult with the generated image + metadata.
    """
    start = time.perf_counter()
    style_weight = style_weight if style_weight is not None else settings.STYLE_WEIGHT
    output_size = output_size or settings.OUTPUT_SIZE

    logger.info(f"text_to_art: query='{query}', top_k={top_k}, alpha={style_weight}")

    # Step 1 — RAG retrieval
    pipeline_ctx = run_rag_pipeline(
        PipelineRequest(query=query, top_k=top_k)
    )

    if not pipeline_ctx.artworks:
        elapsed = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            image=_create_placeholder(output_size),
            image_base64=pil_to_base64(_create_placeholder(output_size)),
            style_reference=None,
            clip_score=0.0,
            generation_time_ms=elapsed,
            query=query,
            message="No reference artworks found for this query. Try a different style description.",
        )

    # Step 2 — Pick best reference
    best_ref = pick_best_reference(pipeline_ctx.artworks, query)

    # Step 3 — Download reference image(s)
    try:
        if use_multi_style and len(pipeline_ctx.artworks) > 1:
            # Multi-style: download top N references
            refs_to_use = pipeline_ctx.artworks[:num_style_refs]
            style_images = []
            for ref in refs_to_use:
                try:
                    img = load_image_from_url(ref.image_url)
                    style_images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to download {ref.title}: {e}")

            if not style_images:
                raise ValueError("Could not download any style reference images")

            # Use first style image as content seed (rotated/transformed)
            content_image = _create_content_seed(style_images[0], output_size)
            result_image = multi_style_transfer(
                content_image, style_images, alpha=style_weight, output_size=output_size
            )
            used_ref = best_ref
        else:
            # Single style
            style_image = load_image_from_url(best_ref.image_url)
            content_image = _create_content_seed(style_image, output_size)
            result_image = style_transfer(
                content_image, style_image, alpha=style_weight, output_size=output_size
            )
            used_ref = best_ref

    except Exception as e:
        logger.error(f"Style transfer failed: {e}")
        elapsed = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            image=_create_placeholder(output_size),
            image_base64=pil_to_base64(_create_placeholder(output_size)),
            style_reference=best_ref,
            clip_score=0.0,
            generation_time_ms=elapsed,
            query=query,
            message=f"Generation failed: {e!s}",
        )

    # Step 4 — Score output
    clip_score = score_output(result_image, query)

    elapsed = int((time.perf_counter() - start) * 1000)

    logger.info(
        f"text_to_art complete: {elapsed}ms, CLIP={clip_score:.4f}, "
        f"ref='{used_ref.title}'"
    )

    return GenerationResult(
        image=result_image,
        image_base64=pil_to_base64(result_image),
        style_reference=used_ref,
        clip_score=clip_score,
        generation_time_ms=elapsed,
        query=query,
        message=(
            f"Generated artwork in the style of '{used_ref.title}' "
            f"by {used_ref.artist} ({used_ref.style}). "
            f"CLIP score: {clip_score:.3f}"
        ),
    )


def style_transfer_from_upload(
    content_image: Image.Image,
    style_query: str,
    top_k: int = 5,
    style_weight: float | None = None,
    output_size: int | None = None,
) -> GenerationResult:
    """
    Style transfer from an uploaded image.

    1. Run RAG pipeline to retrieve style references for the query
    2. CLIP ranker picks the best reference artwork
    3. Download the reference image
    4. Apply AdaIN style transfer: user_image + reference_style → output
    5. Score output with CLIP

    Args:
        content_image:  PIL image uploaded by the user.
        style_query:    Description of the target style.
        top_k:          Number of references to retrieve.
        style_weight:   Style strength (0.0 - 1.0).
        output_size:    Output resolution.

    Returns:
        GenerationResult with the stylized image + metadata.
    """
    start = time.perf_counter()
    style_weight = style_weight if style_weight is not None else settings.STYLE_WEIGHT
    output_size = output_size or settings.OUTPUT_SIZE

    logger.info(
        f"style_transfer_from_upload: query='{style_query}', "
        f"image_size={content_image.size}, alpha={style_weight}"
    )

    # Step 1 — RAG retrieval for style references
    pipeline_ctx = run_rag_pipeline(
        PipelineRequest(query=style_query, top_k=top_k)
    )

    if not pipeline_ctx.artworks:
        elapsed = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            image=content_image,
            image_base64=pil_to_base64(content_image),
            style_reference=None,
            clip_score=0.0,
            generation_time_ms=elapsed,
            query=style_query,
            message="No style references found. Returning original image.",
        )

    # Step 2 — Pick best style reference
    best_ref = pick_best_reference(pipeline_ctx.artworks, style_query)

    # Step 3 — Download style reference
    try:
        style_image = load_image_from_url(best_ref.image_url)
    except Exception as e:
        logger.error(f"Failed to download style reference: {e}")
        elapsed = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            image=content_image,
            image_base64=pil_to_base64(content_image),
            style_reference=best_ref,
            clip_score=0.0,
            generation_time_ms=elapsed,
            query=style_query,
            message=f"Could not download style reference: {e!s}",
        )

    # Step 4 — Apply style transfer
    try:
        result_image = style_transfer(
            content_image, style_image, alpha=style_weight, output_size=output_size
        )
    except Exception as e:
        logger.error(f"Style transfer failed: {e}")
        elapsed = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            image=content_image,
            image_base64=pil_to_base64(content_image),
            style_reference=best_ref,
            clip_score=0.0,
            generation_time_ms=elapsed,
            query=style_query,
            message=f"Style transfer failed: {e!s}",
        )

    # Step 5 — Score output
    clip_score = score_output(result_image, style_query)

    elapsed = int((time.perf_counter() - start) * 1000)

    logger.info(
        f"style_transfer_from_upload complete: {elapsed}ms, "
        f"CLIP={clip_score:.4f}, ref='{best_ref.title}'"
    )

    return GenerationResult(
        image=result_image,
        image_base64=pil_to_base64(result_image),
        style_reference=best_ref,
        clip_score=clip_score,
        generation_time_ms=elapsed,
        query=style_query,
        message=(
            f"Applied style of '{best_ref.title}' by {best_ref.artist} "
            f"({best_ref.style}) to your image. CLIP score: {clip_score:.3f}"
        ),
    )


# ── Helpers ───────────────────────────────────────────────────────────────

def _create_content_seed(
    reference_image: Image.Image,
    size: int,
) -> Image.Image:
    """
    Create a content seed image for text-to-art generation.

    For text-to-art mode, we don't have a user-uploaded content image.
    We create a "content seed" by heavily blurring and desaturating
    the reference image — this gives the output organic structure while
    letting the style dominate.
    """
    from PIL import ImageEnhance, ImageFilter

    # Start from the reference image, resized
    seed = reference_image.copy()
    seed = seed.resize((size, size), Image.LANCZOS)

    # Heavy Gaussian blur — removes detail, keeps broad composition
    seed = seed.filter(ImageFilter.GaussianBlur(radius=15))

    # Desaturate partially — let the style's colors dominate
    enhancer = ImageEnhance.Color(seed)
    seed = enhancer.enhance(0.3)

    # Reduce contrast — flatten to let style features emerge
    enhancer = ImageEnhance.Contrast(seed)
    seed = enhancer.enhance(0.5)

    return seed


def _create_placeholder(size: int) -> Image.Image:
    """Create a gray placeholder image (used when generation fails)."""
    return Image.new("RGB", (size, size), color=(128, 128, 128))
