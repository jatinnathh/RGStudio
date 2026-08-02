"""
RGStudio — HuggingFace Spaces Demo
Gradio interface for the RAG-Powered GAN Art Studio.
Proxies requests to the deployed Railway backend.
"""

import gradio as gr
import requests
import base64
import os
from io import BytesIO
from PIL import Image

API_BASE = os.getenv("RGSTUDIO_API_URL", "https://your-railway-backend.up.railway.app")


def text_to_art(query: str, style_weight: float, top_k: int, output_size: int):
    """Generate artwork from a text description."""
    try:
        response = requests.post(
            f"{API_BASE}/generate",
            json={
                "query": query,
                "style_weight": style_weight,
                "top_k": int(top_k),
                "output_size": int(output_size),
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("image_base64"):
            img_bytes = base64.b64decode(data["image_base64"])
            img = Image.open(BytesIO(img_bytes))

            info = f"CLIP Score: {data.get('clip_score', 'N/A'):.4f}\n"
            info += f"Generation Time: {data.get('generation_time_ms', 0)/1000:.1f}s\n"
            if data.get("style_reference"):
                ref = data["style_reference"]
                info += f"Style: {ref.get('title', '?')} by {ref.get('artist', '?')}"
            return img, info
        else:
            return None, f"Error: {data.get('message', 'Unknown error')}"

    except Exception as e:
        return None, f"Error: {str(e)}"


def style_transfer(image, style_query: str, style_weight: float, top_k: int):
    """Apply style transfer to an uploaded image."""
    try:
        # Convert PIL image to bytes
        buf = BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        response = requests.post(
            f"{API_BASE}/style-transfer",
            files={"image": ("upload.jpg", buf, "image/jpeg")},
            data={
                "style_query": style_query,
                "style_weight": str(style_weight),
                "top_k": str(int(top_k)),
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("image_base64"):
            img_bytes = base64.b64decode(data["image_base64"])
            img = Image.open(BytesIO(img_bytes))

            info = f"CLIP Score: {data.get('clip_score', 'N/A'):.4f}\n"
            info += f"Time: {data.get('generation_time_ms', 0)/1000:.1f}s"
            return img, info
        else:
            return None, f"Error: {data.get('message', 'Unknown error')}"

    except Exception as e:
        return None, f"Error: {str(e)}"


# ── Gradio UI ──────────────────────────────────────────────────────────────

with gr.Blocks(
    title="RGStudio — RAG-Powered GAN Art Studio",
    theme=gr.themes.Soft(primary_hue="amber", secondary_hue="red"),
    css="""
        .gradio-container { max-width: 1200px !important; }
        .output-image { border-radius: 12px; }
    """,
) as demo:
    gr.Markdown(
        """
        # 🎨 RGStudio — RAG-Powered GAN Art Studio

        **Describe an art style → RAG retrieves reference images + artist context →
        CLIP-guided GAN generates a new artwork in that style.**

        Two systems, one seamless pipeline: *Retrieval-Augmented Generation meets Generative Adversarial Networks.*
        """
    )

    with gr.Tabs():
        # ── Tab 1: Text to Art ──
        with gr.TabItem("Text → Art"):
            with gr.Row():
                with gr.Column(scale=1):
                    txt_query = gr.Textbox(
                        label="Style Description",
                        placeholder="impressionist sunset over water, Monet style",
                        lines=3,
                    )
                    txt_weight = gr.Slider(0.0, 1.0, value=0.8, step=0.05, label="Style Weight")
                    txt_topk = gr.Slider(1, 20, value=5, step=1, label="Top K References")
                    txt_size = gr.Slider(256, 1024, value=512, step=128, label="Output Size (px)")
                    txt_btn = gr.Button("Generate Art", variant="primary")

                with gr.Column(scale=2):
                    txt_output = gr.Image(label="Generated Artwork", type="pil")
                    txt_info = gr.Textbox(label="Generation Info", lines=3)

            txt_btn.click(
                fn=text_to_art,
                inputs=[txt_query, txt_weight, txt_topk, txt_size],
                outputs=[txt_output, txt_info],
            )

        # ── Tab 2: Style Transfer ──
        with gr.TabItem("Style Transfer"):
            with gr.Row():
                with gr.Column(scale=1):
                    st_image = gr.Image(label="Upload Your Image", type="pil")
                    st_query = gr.Textbox(
                        label="Target Style",
                        placeholder="cubist Picasso style",
                        lines=2,
                    )
                    st_weight = gr.Slider(0.0, 1.0, value=0.7, step=0.05, label="Style Weight")
                    st_topk = gr.Slider(1, 20, value=5, step=1, label="Top K References")
                    st_btn = gr.Button("Apply Style", variant="primary")

                with gr.Column(scale=2):
                    st_output = gr.Image(label="Styled Result", type="pil")
                    st_info = gr.Textbox(label="Transfer Info", lines=3)

            st_btn.click(
                fn=style_transfer,
                inputs=[st_image, st_query, st_weight, st_topk],
                outputs=[st_output, st_info],
            )

    gr.Markdown(
        """
        ---
        **Tech Stack**: FastAPI · AdaIN (VGG19) · CLIP (ViT-B/32) · Qdrant Cloud · Next.js

        [GitHub](https://github.com/jatinnathh/RGStudio) ·
        [Live App](https://rgstudio.vercel.app) ·
        [API Docs](https://your-railway-backend.up.railway.app/docs)
        """
    )


if __name__ == "__main__":
    demo.launch()
