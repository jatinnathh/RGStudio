# backend/seed_artworks.py
#
# Bulk seed script - run from the `backend/` directory:
#   python -m seed_artworks
#
# Uses the existing ingestion pipeline (CLIP embed -> Qdrant upsert).
# Includes retry logic with exponential backoff for rate-limited requests.

import sys
import time
from rag.ingestion.ingestor import ingest_artwork
from rag.schemas.models import IngestRequest
from rag.vectorstore.qdrant_client import ensure_collection_exists
from rag.utils.logger import get_logger

logger = get_logger(__name__)

# ---- Curated artwork dataset ------------------------------------------------
# Using /thumb/ URLs where possible (smaller, friendlier to Wikimedia)

ARTWORKS = [
    # --- Impressionism --------------------------------------------------------
    {
        "title": "Water Lilies",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1906,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg/800px-Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg",
        "tags": ["water", "lilies", "pond", "flowers", "nature"],
    },
    {
        "title": "Impression, Sunrise",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1872,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Monet_-_Impression%2C_Sunrise.jpg/800px-Monet_-_Impression%2C_Sunrise.jpg",
        "tags": ["sunrise", "harbor", "boats", "fog", "orange"],
    },
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "style": "Post-Impressionism",
        "year": 1886,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/800px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
        "tags": ["park", "pointillism", "people", "river", "leisure"],
    },
    {
        "title": "Dance at Le Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1876,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg/800px-Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg",
        "tags": ["dance", "party", "garden", "people", "light"],
    },

    # --- Renaissance ----------------------------------------------------------
    {
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1503,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "tags": ["portrait", "smile", "woman", "landscape", "iconic"],
    },
    {
        "title": "The Birth of Venus",
        "artist": "Sandro Botticelli",
        "style": "Renaissance",
        "year": 1485,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/800px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
        "tags": ["venus", "mythology", "shell", "sea", "goddess"],
    },
    {
        "title": "The Creation of Adam",
        "artist": "Michelangelo",
        "style": "Renaissance",
        "year": 1512,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg/800px-Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg",
        "tags": ["god", "adam", "hands", "ceiling", "fresco"],
    },
    {
        "title": "The School of Athens",
        "artist": "Raphael",
        "style": "Renaissance",
        "year": 1511,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg/800px-%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg",
        "tags": ["philosophy", "architecture", "scholars", "fresco", "classical"],
    },

    # --- Baroque --------------------------------------------------------------
    {
        "title": "Girl with a Pearl Earring",
        "artist": "Johannes Vermeer",
        "style": "Baroque",
        "year": 1665,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/800px-1665_Girl_with_a_Pearl_Earring.jpg",
        "tags": ["portrait", "pearl", "girl", "turban", "earring"],
    },
    {
        "title": "The Night Watch",
        "artist": "Rembrandt",
        "style": "Baroque",
        "year": 1642,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/The_Night_Watch_-_HD.jpg/800px-The_Night_Watch_-_HD.jpg",
        "tags": ["militia", "group", "night", "dramatic", "lighting"],
    },

    # --- Post-Impressionism ---------------------------------------------------
    {
        "title": "Cafe Terrace at Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg/800px-Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg",
        "tags": ["cafe", "night", "stars", "yellow", "street"],
    },
    {
        "title": "Sunflowers",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Vincent_Willem_van_Gogh_127.jpg/800px-Vincent_Willem_van_Gogh_127.jpg",
        "tags": ["sunflowers", "vase", "yellow", "still life", "flowers"],
    },
    {
        "title": "Self-Portrait with Bandaged Ear",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1889,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Vincent_Willem_van_Gogh_-_Self-Portrait_with_Bandaged_Ear_%28Courtauld_Institute%29.jpg/800px-Vincent_Willem_van_Gogh_-_Self-Portrait_with_Bandaged_Ear_%28Courtauld_Institute%29.jpg",
        "tags": ["self-portrait", "bandage", "ear", "face", "coat"],
    },

    # --- Expressionism --------------------------------------------------------
    {
        "title": "The Scream",
        "artist": "Edvard Munch",
        "style": "Expressionism",
        "year": 1893,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/800px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
        "tags": ["scream", "anxiety", "sky", "bridge", "figure"],
    },

    # --- Ukiyo-e / Romanticism ------------------------------------------------
    {
        "title": "The Great Wave off Kanagawa",
        "artist": "Katsushika Hokusai",
        "style": "Ukiyo-e",
        "year": 1831,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/800px-Tsunami_by_hokusai_19th_century.jpg",
        "tags": ["wave", "ocean", "japan", "boats", "mount fuji"],
    },
    {
        "title": "Wanderer above the Sea of Fog",
        "artist": "Caspar David Friedrich",
        "style": "Romanticism",
        "year": 1818,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg/800px-Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg",
        "tags": ["wanderer", "fog", "mountains", "solitude", "landscape"],
    },
    {
        "title": "Liberty Leading the People",
        "artist": "Eugene Delacroix",
        "style": "Romanticism",
        "year": 1830,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg/800px-Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg",
        "tags": ["liberty", "revolution", "flag", "france", "battle"],
    },

    # --- Cubism ---------------------------------------------------------------
    {
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1937,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Guernica.jpg",
        "tags": ["war", "bombing", "pain", "monochrome", "political"],
    },
    {
        "title": "Les Demoiselles d'Avignon",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1907,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/4/4c/Les_Demoiselles_d%27Avignon.jpg",
        "tags": ["women", "angular", "african", "masks", "nude"],
    },

    # --- Surrealism -----------------------------------------------------------
    {
        "title": "The Son of Man",
        "artist": "Rene Magritte",
        "style": "Surrealism",
        "year": 1964,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/e/e5/Magritte_TheSonOfMan.jpg",
        "tags": ["apple", "face", "bowler hat", "mystery", "man"],
    },
    {
        "title": "The Elephants",
        "artist": "Salvador Dali",
        "style": "Surrealism",
        "year": 1948,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/1/15/Dali_elephants.jpg",
        "tags": ["elephants", "long legs", "desert", "dreamlike", "surreal"],
    },

    # --- Abstract / Modern ----------------------------------------------------
    {
        "title": "Composition VIII",
        "artist": "Wassily Kandinsky",
        "style": "Abstract",
        "year": 1923,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/800px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
        "tags": ["geometric", "shapes", "circles", "lines", "colorful"],
    },
    {
        "title": "Broadway Boogie Woogie",
        "artist": "Piet Mondrian",
        "style": "De Stijl",
        "year": 1943,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg/800px-Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg",
        "tags": ["grid", "primary colors", "geometric", "city", "jazz"],
    },
    {
        "title": "Number 1A, 1948",
        "artist": "Jackson Pollock",
        "style": "Abstract Expressionism",
        "year": 1948,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/b/b7/Pollock-No._5.jpg",
        "tags": ["drip", "splatter", "abstract", "chaotic", "paint"],
    },

    # --- Pop Art --------------------------------------------------------------
    {
        "title": "Campbell's Soup Cans",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/9/95/Campbell%27s_Soup_Cans_MOMA_reduced_80%25.jpg",
        "tags": ["soup", "cans", "consumer", "repetition", "commercial"],
    },

    # --- Realism --------------------------------------------------------------
    {
        "title": "American Gothic",
        "artist": "Grant Wood",
        "style": "Realism",
        "year": 1930,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/800px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
        "tags": ["couple", "farm", "pitchfork", "rural", "gothic"],
    },
    {
        "title": "Nighthawks",
        "artist": "Edward Hopper",
        "style": "Realism",
        "year": 1942,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Nighthawks_by_Edward_Hopper_1942.jpg/800px-Nighthawks_by_Edward_Hopper_1942.jpg",
        "tags": ["diner", "night", "urban", "loneliness", "city"],
    },
]


# ---- Retry helper ------------------------------------------------------------

MAX_RETRIES = 3
BASE_DELAY = 3          # seconds between each artwork
RETRY_BACKOFF = [5, 10, 20]  # seconds to wait on 1st, 2nd, 3rd retry


def ingest_with_retry(art: dict, index: int, total: int) -> bool:
    """Attempt to ingest an artwork with retry on failure."""
    title = art["title"]
    artist = art["artist"]

    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                wait = RETRY_BACKOFF[attempt - 1]
                print(f"         [RETRY {attempt}/{MAX_RETRIES}] Waiting {wait}s...")
                time.sleep(wait)

            request = IngestRequest(**art)
            result = ingest_artwork(request)

            if result.success:
                print(f"         [OK] Done - ID: {result.artwork_id}")
                return True
            else:
                print(f"         [FAIL] {result.message}")

        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str
            if is_rate_limit and attempt < MAX_RETRIES:
                print(f"         [RATE-LIMITED] {err_str[:80]}...")
                continue
            else:
                print(f"         [FAIL] Error: {err_str[:120]}")
                return False

    return False


def main():
    """Ingest all artworks into Qdrant, using the existing pipeline."""
    ensure_collection_exists()

    total = len(ARTWORKS)
    success = 0
    failed = 0
    skipped_titles = []

    print(f"\n{'='*60}")
    print(f"  Seeding {total} artworks into Qdrant")
    print(f"  (with retry + {BASE_DELAY}s delay between requests)")
    print(f"{'='*60}\n")

    for i, art in enumerate(ARTWORKS, 1):
        print(f"[{i}/{total}] Ingesting: \"{art['title']}\" by {art['artist']}...")

        if ingest_with_retry(art, i, total):
            success += 1
        else:
            failed += 1
            skipped_titles.append(art["title"])

        # Respect Wikimedia rate limits
        time.sleep(BASE_DELAY)

    print(f"\n{'='*60}")
    print(f"  Seeding complete!")
    print(f"  Success: {success}/{total}")
    print(f"  Failed:  {failed}/{total}")
    if skipped_titles:
        print(f"  Skipped: {', '.join(skipped_titles)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

