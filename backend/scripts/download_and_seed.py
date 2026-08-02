# backend/scripts/download_and_seed.py
# -*- coding: utf-8 -*-
r"""
Production seed script for RGStudio.

1. Downloads artwork images from Wikimedia into art_dataset/{artist_slug}/
2. Ingests each artwork into Qdrant with a local image_path
3. FastAPI serves images via /images/{artist}/{filename}.jpg

Usage:
    cd backend
    python -m scripts.download_and_seed
"""
import sys, io, os, re, time, json, hashlib
from pathlib import Path
from urllib.parse import unquote

# Force UTF-8 stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
from PIL import Image

# ── Setup paths ──────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "art_dataset"
DATASET_DIR.mkdir(exist_ok=True)

# Add backend to path for imports
sys.path.insert(0, str(BACKEND_DIR))

from rag.embeddings.clip_encoder import encode_image_from_file
from rag.vectorstore.qdrant_client import ensure_collection_exists, recreate_collection, upsert_artwork
from rag.schemas.models import ArtworkMetadata
from rag.utils.logger import get_logger

logger = get_logger(__name__)

WIKIMEDIA_UA = "RGStudioBot/1.0 (art-generation-project; contact@rgstudio.dev)"


# ── Helpers ──────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '_', text)
    return text[:80]


def resolve_wikimedia_url(filename: str, wiki_domain: str = "commons") -> str | None:
    """Use the Wikimedia API to get a valid download URL for a file."""
    try:
        if wiki_domain == "commons":
            api_url = "https://commons.wikimedia.org/w/api.php"
        else:
            api_url = "https://en.wikipedia.org/w/api.php"

        resp = requests.get(
            api_url,
            params={
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 320,
                "format": "json",
            },
            headers={"User-Agent": WIKIMEDIA_UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                # Prefer full original URL (no thumb restrictions), fallback to 320px thumb
                return imageinfo[0].get("url") or imageinfo[0].get("thumburl")
    except Exception as e:
        logger.warning(f"API resolve failed for {filename}: {e}")

    # Fallback: strip thumb path if present
    stripped = re.sub(r'/thumb/([^/]+/[^/]+/[^/]+)/\d+px-[^/]+$', r'/\1', filename)
    return f"https://upload.wikimedia.org/wikipedia/{wiki_domain}/{stripped}" if "/" in stripped else None


def search_wikimedia_commons(title: str, artist: str) -> str | None:
    """Use Wikimedia Commons search API to find the working image file URL."""
    try:
        query = f"{title} {artist}"
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": 6,
                "format": "json",
            },
            headers={"User-Agent": WIKIMEDIA_UA},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])
        if results:
            first_file = results[0]["title"].replace("File:", "")
            return resolve_wikimedia_url(first_file, "commons")
    except Exception as e:
        logger.warning(f"Search API failed for '{title}': {e}")
    return None


def extract_filename_from_url(url: str) -> tuple[str, str]:
    """Extract the Wikimedia filename and domain from a URL."""
    # /wikipedia/commons/... or /wikipedia/en/...
    match = re.search(r'/wikipedia/(commons|en)/', url)
    domain = match.group(1) if match else "commons"

    # Extract filename from thumb URL or direct URL
    thumb_match = re.search(r'/thumb/[^/]+/[^/]+/([^/]+)/\d+px-', url)
    if thumb_match:
        return unquote(thumb_match.group(1)), domain

    # Direct URL: last path segment
    filename = unquote(url.rstrip('/').split('/')[-1])
    return filename, domain


def download_image(url: str, save_path: Path) -> bool:
    """Download an image from a URL, resize, and save as JPEG."""
    try:
        resp = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": WIKIMEDIA_UA},
            stream=True,
        )
        resp.raise_for_status()

        # Read max 40MB
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 40 * 1024 * 1024:
                logger.warning(f"Image too large, skipping: {url[:80]}")
                return False

        image = Image.open(io.BytesIO(content)).convert("RGB")

        # Resize to max 800px on longest side (good quality for style transfer)
        image.thumbnail((800, 800), Image.LANCZOS)

        # Save as JPEG
        save_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(save_path), "JPEG", quality=92)

        return True

    except Exception as e:
        logger.warning(f"Download failed: {e}")
        return False


# ── Artwork Dataset ──────────────────────────────────────────────────────
# Each artwork has a Wikimedia source URL for downloading.
# After download, images are stored locally and Qdrant stores the local path.

ARTWORKS = [

    # -- IMPRESSIONISM (6) -------
    {
        "title": "Water Lilies",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1906,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg/640px-Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg",
        "tags": ["water", "lilies", "pond", "reflection", "nature"],
    },
    {
        "title": "Impression, Sunrise",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1872,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Monet_-_Impression%2C_Sunrise.jpg/640px-Monet_-_Impression%2C_Sunrise.jpg",
        "tags": ["sunrise", "harbor", "boats", "fog", "orange light"],
    },
    {
        "title": "Dance at Le Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1876,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg/640px-Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg",
        "tags": ["dance", "party", "garden", "dappled light", "social"],
    },
    {
        "title": "The Luncheon of the Boating Party",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1881,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Auguste_Renoir_-_Luncheon_of_the_Boating_Party_-_Google_Art_Project.jpg/640px-Auguste_Renoir_-_Luncheon_of_the_Boating_Party_-_Google_Art_Project.jpg",
        "tags": ["lunch", "boating", "summer", "social gathering", "river"],
    },
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "style": "Impressionism",
        "year": 1886,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/640px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
        "tags": ["park", "pointillism", "dotted", "people", "river"],
    },
    {
        "title": "The Ballet Class",
        "artist": "Edgar Degas",
        "style": "Impressionism",
        "year": 1874,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Degas_-_The_Ballet_Class.jpg/640px-Degas_-_The_Ballet_Class.jpg",
        "tags": ["ballet", "dancers", "studio", "movement", "rehearsal"],
    },

    # -- POST-IMPRESSIONISM (5) -------
    {
        "title": "The Starry Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1889,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/640px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "tags": ["night", "swirling", "stars", "village", "sky"],
    },
    {
        "title": "Cafe Terrace at Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg/640px-Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg",
        "tags": ["cafe", "night", "yellow", "stars", "cobblestone"],
    },
    {
        "title": "Sunflowers",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Vincent_Willem_van_Gogh_127.jpg/640px-Vincent_Willem_van_Gogh_127.jpg",
        "tags": ["sunflowers", "yellow", "vase", "still life", "warm"],
    },
    {
        "title": "Mont Sainte-Victoire",
        "artist": "Paul Cezanne",
        "style": "Post-Impressionism",
        "year": 1904,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Paul_C%C3%A9zanne_-_Mont_Sainte-Victoire_-_Google_Art_Project.jpg/640px-Paul_C%C3%A9zanne_-_Mont_Sainte-Victoire_-_Google_Art_Project.jpg",
        "tags": ["mountain", "landscape", "structured", "geometric", "provence"],
    },
    {
        "title": "Where Do We Come From",
        "artist": "Paul Gauguin",
        "style": "Post-Impressionism",
        "year": 1898,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Paul_Gauguin_-_D%27ou_venons-nous.jpg/640px-Paul_Gauguin_-_D%27ou_venons-nous.jpg",
        "tags": ["tropical", "figures", "spiritual", "tahiti", "existential"],
    },

    # -- RENAISSANCE (5) -------
    {
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1503,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/640px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "tags": ["portrait", "smile", "woman", "sfumato", "iconic"],
    },
    {
        "title": "The Birth of Venus",
        "artist": "Sandro Botticelli",
        "style": "Renaissance",
        "year": 1485,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/640px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
        "tags": ["venus", "goddess", "shell", "sea", "mythological"],
    },
    {
        "title": "The Creation of Adam",
        "artist": "Michelangelo",
        "style": "Renaissance",
        "year": 1512,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg/640px-Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg",
        "tags": ["god", "adam", "touch", "ceiling", "divine"],
    },
    {
        "title": "The School of Athens",
        "artist": "Raphael",
        "style": "Renaissance",
        "year": 1511,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg/640px-%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg",
        "tags": ["philosophy", "scholars", "architecture", "arched", "fresco"],
    },
    {
        "title": "The Last Supper",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1498,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/%C3%9Altima_Cena_-_Da_Vinci_5.jpg/640px-%C3%9Altima_Cena_-_Da_Vinci_5.jpg",
        "tags": ["jesus", "disciples", "meal", "dramatic", "biblical"],
    },

    # -- BAROQUE (4) -------
    {
        "title": "Girl with a Pearl Earring",
        "artist": "Johannes Vermeer",
        "style": "Baroque",
        "year": 1665,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/640px-1665_Girl_with_a_Pearl_Earring.jpg",
        "tags": ["portrait", "pearl", "turban", "light", "intimate"],
    },
    {
        "title": "The Night Watch",
        "artist": "Rembrandt",
        "style": "Baroque",
        "year": 1642,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/The_Night_Watch_-_HD.jpg/640px-The_Night_Watch_-_HD.jpg",
        "tags": ["militia", "dramatic lighting", "group", "chiaroscuro", "Dutch"],
    },
    {
        "title": "The Calling of Saint Matthew",
        "artist": "Caravaggio",
        "style": "Baroque",
        "year": 1600,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Caravaggio_-_La_vocazione_di_san_Matteo.jpg/640px-Caravaggio_-_La_vocazione_di_san_Matteo.jpg",
        "tags": ["chiaroscuro", "dramatic", "light", "biblical", "shadow"],
    },
    {
        "title": "Las Meninas",
        "artist": "Diego Velazquez",
        "style": "Baroque",
        "year": 1656,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Las_Meninas_01.jpg/640px-Las_Meninas_01.jpg",
        "tags": ["Spanish court", "princess", "mirror", "complex", "royal"],
    },

    # -- ROMANTICISM (4) -------
    {
        "title": "Wanderer above the Sea of Fog",
        "artist": "Caspar David Friedrich",
        "style": "Romanticism",
        "year": 1818,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg/640px-Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg",
        "tags": ["solitude", "mountains", "fog", "sublime", "silhouette"],
    },
    {
        "title": "Liberty Leading the People",
        "artist": "Eugene Delacroix",
        "style": "Romanticism",
        "year": 1830,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg/640px-Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg",
        "tags": ["revolution", "flag", "allegory", "battle", "freedom"],
    },
    {
        "title": "The Fighting Temeraire",
        "artist": "J.M.W. Turner",
        "style": "Romanticism",
        "year": 1839,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/The_Fighting_Temeraire%2C_JMW_Turner%2C_National_Gallery.jpg/640px-The_Fighting_Temeraire%2C_JMW_Turner%2C_National_Gallery.jpg",
        "tags": ["ship", "sunset", "steam", "sea", "nostalgia"],
    },
    {
        "title": "Saturn Devouring His Son",
        "artist": "Francisco Goya",
        "style": "Romanticism",
        "year": 1823,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Francisco_de_Goya%2C_Saturno_devorando_a_su_hijo_%281819-1823%29.jpg/640px-Francisco_de_Goya%2C_Saturno_devorando_a_su_hijo_%281819-1823%29.jpg",
        "tags": ["dark", "horror", "mythological", "savage", "intense"],
    },

    # -- REALISM (3) -------
    {
        "title": "American Gothic",
        "artist": "Grant Wood",
        "style": "Realism",
        "year": 1930,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/640px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
        "tags": ["rural", "farm", "couple", "pitchfork", "americana"],
    },
    {
        "title": "Nighthawks",
        "artist": "Edward Hopper",
        "style": "Realism",
        "year": 1942,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Nighthawks_by_Edward_Hopper_1942.jpg/640px-Nighthawks_by_Edward_Hopper_1942.jpg",
        "tags": ["diner", "night", "urban", "loneliness", "neon"],
    },
    {
        "title": "The Gleaners",
        "artist": "Jean-Francois Millet",
        "style": "Realism",
        "year": 1857,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Jean-Fran%C3%A7ois_Millet_-_Gleaners_-_Google_Art_Project_2.jpg/640px-Jean-Fran%C3%A7ois_Millet_-_Gleaners_-_Google_Art_Project_2.jpg",
        "tags": ["peasants", "harvest", "field", "labor", "countryside"],
    },

    # -- EXPRESSIONISM (4) -------
    {
        "title": "The Scream",
        "artist": "Edvard Munch",
        "style": "Expressionism",
        "year": 1893,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/640px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
        "tags": ["anguish", "sky", "wavy", "bridge", "figure"],
    },
    {
        "title": "Portrait of Dr. Gachet",
        "artist": "Vincent van Gogh",
        "style": "Expressionism",
        "year": 1890,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Van_Gogh_-_Portrait_of_Dr._Gachet.jpg/640px-Van_Gogh_-_Portrait_of_Dr._Gachet.jpg",
        "tags": ["portrait", "melancholy", "doctor", "foxglove", "emotional"],
    },
    {
        "title": "The Large Blue Horses",
        "artist": "Franz Marc",
        "style": "Expressionism",
        "year": 1911,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Franz_Marc_-_The_Large_Blue_Horses_-_Google_Art_Project.jpg/640px-Franz_Marc_-_The_Large_Blue_Horses_-_Google_Art_Project.jpg",
        "tags": ["blue", "horses", "animals", "vivid", "emotional"],
    },
    {
        "title": "The Kiss",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1908,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/The_Kiss_-_Gustav_Klimt_-_Google_Cultural_Institute.jpg/640px-The_Kiss_-_Gustav_Klimt_-_Google_Cultural_Institute.jpg",
        "tags": ["gold", "embrace", "lovers", "ornate", "tender"],
    },

    # -- CUBISM (3) -------
    {
        "title": "Les Demoiselles d'Avignon",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1907,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/4/4c/Les_Demoiselles_d%27Avignon.jpg",
        "tags": ["angular", "African masks", "deconstructed", "female", "proto-cubist"],
    },
    {
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1937,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Guernica.jpg",
        "tags": ["war", "monochrome", "fragmented", "suffering", "political"],
    },
    {
        "title": "Man with a Guitar",
        "artist": "Georges Braque",
        "style": "Cubism",
        "year": 1911,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Georges_Braque%2C_1911-12%2C_Man_with_a_Guitar%2C_oil_on_canvas%2C_116.2_x_80.9_cm%2C_Museum_of_Modern_Art%2C_New_York.jpg/640px-Georges_Braque%2C_1911-12%2C_Man_with_a_Guitar%2C_oil_on_canvas%2C_116.2_x_80.9_cm%2C_Museum_of_Modern_Art%2C_New_York.jpg",
        "tags": ["analytic cubism", "monochrome", "fractured", "guitar", "planes"],
    },

    # -- SURREALISM (4) -------
    {
        "title": "The Persistence of Memory",
        "artist": "Salvador Dali",
        "style": "Surrealism",
        "year": 1931,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg",
        "tags": ["melting clocks", "desert", "dreamlike", "time", "distorted"],
    },
    {
        "title": "The Son of Man",
        "artist": "Rene Magritte",
        "style": "Surrealism",
        "year": 1964,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/e/e5/Magritte_TheSonOfMan.jpg",
        "tags": ["apple", "bowler hat", "mystery", "concealment", "man"],
    },
    {
        "title": "The Treachery of Images",
        "artist": "Rene Magritte",
        "style": "Surrealism",
        "year": 1929,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/b/b9/MagrittePipe.jpg",
        "tags": ["pipe", "text", "conceptual", "philosophical", "iconic"],
    },
    {
        "title": "I and the Village",
        "artist": "Marc Chagall",
        "style": "Surrealism",
        "year": 1911,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/0/0c/I_and_the_Village.jpg",
        "tags": ["village", "goat", "folklore", "dreamlike", "colorful"],
    },

    # -- ABSTRACT (4) -------
    {
        "title": "Composition VIII",
        "artist": "Wassily Kandinsky",
        "style": "Abstract",
        "year": 1923,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/640px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
        "tags": ["geometric", "circles", "lines", "colorful", "musical"],
    },
    {
        "title": "Broadway Boogie Woogie",
        "artist": "Piet Mondrian",
        "style": "De Stijl",
        "year": 1943,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg/640px-Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg",
        "tags": ["grid", "primary colors", "geometric", "city", "jazz"],
    },
    {
        "title": "Black Square",
        "artist": "Kazimir Malevich",
        "style": "Suprematism",
        "year": 1915,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/f/f5/Malevich_black_square.jpg",
        "tags": ["black", "square", "conceptual", "suprematist", "void"],
    },
    {
        "title": "Number 1A",
        "artist": "Jackson Pollock",
        "style": "Abstract Expressionism",
        "year": 1948,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/b/b7/Pollock-No._5.jpg",
        "tags": ["drip painting", "splatter", "chaotic", "action painting", "raw"],
    },

    # -- POP ART (3) -------
    {
        "title": "Campbell's Soup Cans",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/9/95/Campbell%27s_Soup_Cans_MOMA_reduced_80%25.jpg",
        "tags": ["consumer", "repetition", "commercial", "cans", "bold"],
    },
    {
        "title": "Whaam!",
        "artist": "Roy Lichtenstein",
        "style": "Pop Art",
        "year": 1963,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/2/29/Roy_Lichtenstein_Whaam.jpg",
        "tags": ["comic", "bold lines", "war", "fighter jet", "benday dots"],
    },
    {
        "title": "Marilyn Diptych",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "source_url": "https://upload.wikimedia.org/wikipedia/en/b/b2/Warhol-Monroe.jpg",
        "tags": ["celebrity", "silk screen", "repetition", "Marilyn Monroe", "faded"],
    },

    # -- UKIYO-E (3) -------
    {
        "title": "The Great Wave off Kanagawa",
        "artist": "Katsushika Hokusai",
        "style": "Ukiyo-e",
        "year": 1831,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/640px-Tsunami_by_hokusai_19th_century.jpg",
        "tags": ["wave", "ocean", "Japan", "Mount Fuji", "woodblock"],
    },
    {
        "title": "Fine Wind, Clear Morning",
        "artist": "Katsushika Hokusai",
        "style": "Ukiyo-e",
        "year": 1830,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Red_Fuji_southern_wind_clear_morning.jpg/640px-Red_Fuji_southern_wind_clear_morning.jpg",
        "tags": ["Mount Fuji", "red", "sky", "Japan", "woodblock"],
    },
    {
        "title": "Sudden Shower over Shin-Ohashi Bridge",
        "artist": "Utagawa Hiroshige",
        "style": "Ukiyo-e",
        "year": 1857,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Hiroshige_Ohashi_Atake.jpg/640px-Hiroshige_Ohashi_Atake.jpg",
        "tags": ["rain", "bridge", "woodblock", "Japan", "storm"],
    },

    # -- NEOCLASSICISM (3) -------
    {
        "title": "Napoleon Crossing the Alps",
        "artist": "Jacques-Louis David",
        "style": "Neoclassicism",
        "year": 1801,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/David_-_Napoleon_crossing_the_Alps_-_Malmaison2.jpg/640px-David_-_Napoleon_crossing_the_Alps_-_Malmaison2.jpg",
        "tags": ["Napoleon", "horse", "heroic", "dramatic", "mountain"],
    },
    {
        "title": "Oath of the Horatii",
        "artist": "Jacques-Louis David",
        "style": "Neoclassicism",
        "year": 1784,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Jacques-Louis_David_-_Oath_of_the_Horatii_-_Google_Art_Project.jpg/640px-Jacques-Louis_David_-_Oath_of_the_Horatii_-_Google_Art_Project.jpg",
        "tags": ["swords", "soldiers", "honor", "Roman", "patriotism"],
    },
    {
        "title": "Psyche Revived by Cupid's Kiss",
        "artist": "Antonio Canova",
        "style": "Neoclassicism",
        "year": 1787,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Psyche_revived_Louvre_MR1777.jpg/640px-Psyche_revived_Louvre_MR1777.jpg",
        "tags": ["sculpture", "marble", "love", "mythology", "tender"],
    },

    # -- SYMBOLISM (2) -------
    {
        "title": "Ophelia",
        "artist": "John Everett Millais",
        "style": "Symbolism",
        "year": 1852,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/John_Everett_Millais_-_Ophelia_-_Google_Art_Project.jpg/640px-John_Everett_Millais_-_Ophelia_-_Google_Art_Project.jpg",
        "tags": ["water", "flowers", "drowning", "Pre-Raphaelite", "woman"],
    },
    {
        "title": "The Isle of the Dead",
        "artist": "Arnold Bocklin",
        "style": "Symbolism",
        "year": 1883,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/B%C3%B6cklin%2C_arnold%2C_die_toteninsel%2C_dritte_fassung%2C_%C3%B6l_auf_holz%2C_1883%2C_80x150cm.jpg/640px-B%C3%B6cklin%2C_arnold%2C_die_toteninsel%2C_dritte_fassung%2C_%C3%B6l_auf_holz%2C_1883%2C_80x150cm.jpg",
        "tags": ["island", "death", "dark", "trees", "mysterious"],
    },

    # -- ART NOUVEAU (2) -------
    {
        "title": "Portrait of Adele Bloch-Bauer I",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1907,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Klimt_-_Adele_Bloch-Bauer_I.jpg/640px-Klimt_-_Adele_Bloch-Bauer_I.jpg",
        "tags": ["gold", "ornate", "woman", "geometric", "luxury"],
    },
    {
        "title": "The Beethoven Frieze",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1902,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Klimt_Beethovenfries_1.jpg/640px-Klimt_Beethovenfries_1.jpg",
        "tags": ["frieze", "symbolist", "longing", "gold", "figures"],
    },

    # -- PROPAGANDA / STREET ART (2) -------
    {
        "title": "We Can Do It",
        "artist": "J. Howard Miller",
        "style": "Propaganda Poster",
        "year": 1943,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/We_Can_Do_It%21.jpg/640px-We_Can_Do_It%21.jpg",
        "tags": ["poster", "woman", "bold", "patriotic", "iconic"],
    },
    {
        "title": "Metropolis Film Poster",
        "artist": "Heinz Schulz-Neudamm",
        "style": "Art Deco",
        "year": 1927,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Metropolis_%281927_film_poster%29.jpg/640px-Metropolis_%281927_film_poster%29.jpg",
        "tags": ["poster", "robot", "city", "geometric", "futuristic"],
    },

    # -- FUTURISM (2) -------
    {
        "title": "The City Rises",
        "artist": "Umberto Boccioni",
        "style": "Futurism",
        "year": 1910,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Umberto_Boccioni_005.jpg/640px-Umberto_Boccioni_005.jpg",
        "tags": ["horses", "labor", "movement", "modern city", "energy"],
    },
    {
        "title": "Abstract Speed + Sound",
        "artist": "Giacomo Balla",
        "style": "Futurism",
        "year": 1913,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Giacomo_Balla%2C_1913-14%2C_Abstract_Speed_%2B_Sound%2C_oil_on_cardboard%2C_54.5_x_76.5_cm%2C_Peggy_Guggenheim_Collection%2C_Venice.jpg/640px-Giacomo_Balla%2C_1913-14%2C_Abstract_Speed_%2B_Sound%2C_oil_on_cardboard%2C_54.5_x_76.5_cm%2C_Peggy_Guggenheim_Collection%2C_Venice.jpg",
        "tags": ["speed", "sound", "abstraction", "dynamic", "colorful"],
    },

    # -- ROCOCO (2) -------
    {
        "title": "The Swing",
        "artist": "Jean-Honore Fragonard",
        "style": "Rococo",
        "year": 1767,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Fragonard%2C_The_Swing.jpg/640px-Fragonard%2C_The_Swing.jpg",
        "tags": ["swing", "garden", "playful", "pastel", "flirtatious"],
    },
    {
        "title": "Pilgrimage to Cythera",
        "artist": "Antoine Watteau",
        "style": "Rococo",
        "year": 1717,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Watteau_-_Pilgrimage_to_Cythera%2C_Louvre.JPG/640px-Watteau_-_Pilgrimage_to_Cythera%2C_Louvre.JPG",
        "tags": ["pastoral", "lovers", "island", "mythological", "elegant"],
    },
]


# ── Main ─────────────────────────────────────────────────────────────────

def process_artwork(art: dict, index: int, total: int) -> bool:
    """Download image, CLIP-embed, and upsert to Qdrant."""
    artist_slug = slugify(art["artist"])
    title_slug = slugify(art["title"])
    filename = f"{title_slug}.jpg"
    local_dir = DATASET_DIR / artist_slug
    local_path = local_dir / filename

    # 1. Check if already downloaded
    if local_path.exists():
        print(f"         [CACHED] {local_path.relative_to(BACKEND_DIR)}")
    else:
        # Resolve the URL via Wikimedia API
        wiki_filename, wiki_domain = extract_filename_from_url(art["source_url"])
        resolved_url = resolve_wikimedia_url(wiki_filename, wiki_domain)

        if not resolved_url:
            # Fallback: try stripping thumb parameters from source URL directly
            resolved_url = re.sub(r'/thumb/([^/]+/[^/]+/[^/]+)/\d+px-[^/]+$', r'/\1', art["source_url"])

        print(f"         [DOWNLOAD] {wiki_filename[:60]}...")
        if not download_image(resolved_url, local_path):
            # Fallback 2: try searching Wikimedia Commons dynamically
            search_url = search_wikimedia_commons(art["title"], art["artist"])
            if search_url and download_image(search_url, local_path):
                logger.info(f"Downloaded via Commons Search API for {art['title']}")
            else:
                print(f"         [FAIL] Could not download image")
                return False

    # 2. CLIP-embed the local file
    try:
        vector = encode_image_from_file(str(local_path))
    except Exception as e:
        print(f"         [FAIL] CLIP encoding: {e}")
        return False

    # 3. Build metadata — image_path is relative to art_dataset/
    relative_path = f"{artist_slug}/{filename}"
    caption = f"A painting in {art['style']} style by {art['artist']}"

    metadata = ArtworkMetadata(
        title=art["title"],
        artist=art["artist"],
        style=art["style"],
        year=art.get("year"),
        caption=caption,
        image_url=f"/images/{relative_path}",  # Served by FastAPI StaticFiles
        tags=art.get("tags", []),
    )

    # 4. Upsert to Qdrant
    upsert_artwork(
        artwork_id=metadata.id,
        vector=vector,
        payload=metadata.model_dump(mode="json"),
    )

    print(f"         [OK] /images/{relative_path} -> Qdrant {metadata.id}")
    return True


def main():
    recreate_collection()

    total = len(ARTWORKS)
    success = 0
    failed = []

    print(f"\n{'='*64}")
    print(f"  RGStudio - Local-First Art Dataset Seeder")
    print(f"  {total} artworks -> art_dataset/ -> Qdrant")
    print(f"{'='*64}\n")

    for i, art in enumerate(ARTWORKS, 1):
        print(f"[{i:>3}/{total}] {art['style']:<28} '{art['title']}' by {art['artist']}")

        if process_artwork(art, i, total):
            success += 1
        else:
            failed.append(art["title"])

        # Small delay between Wikimedia API calls
        if i < total:
            time.sleep(2)

    print(f"\n{'='*64}")
    print(f"  Done! {success}/{total} artworks downloaded + ingested")
    if failed:
        print(f"\n  Failed ({len(failed)}):")
        for t in failed:
            print(f"    - {t}")
    print(f"\n  Dataset dir: {DATASET_DIR}")
    print(f"  Serve via:   GET /images/<artist>/<title>.jpg")
    print(f"{'='*64}\n")

    # Save a manifest for reference
    manifest = {
        "total": total,
        "success": success,
        "failed": failed,
        "artworks": [
            {
                "title": a["title"],
                "artist": a["artist"],
                "style": a["style"],
                "image_path": f"{slugify(a['artist'])}/{slugify(a['title'])}.jpg",
            }
            for a in ARTWORKS
            if a["title"] not in failed
        ],
    }
    manifest_path = DATASET_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Manifest saved: {manifest_path}\n")


if __name__ == "__main__":
    main()
