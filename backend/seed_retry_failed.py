# backend/seed_retry_failed.py
#
# Retry ONLY the artworks that failed in previous runs.
# Run after waiting a few minutes for Wikimedia rate limits to reset:
#   python -m seed_retry_failed
#
# Uses 10s delay between requests + retry with longer backoff.

import time
from rag.ingestion.ingestor import ingest_artwork
from rag.schemas.models import IngestRequest
from rag.vectorstore.qdrant_client import ensure_collection_exists
from rag.utils.logger import get_logger

logger = get_logger(__name__)

# Only the artworks that failed in previous runs.
# - /wikipedia/en/ images: use original URL (fair-use, no thumb support)
# - /wikipedia/commons/ images: use 640px thumbnails (smaller = more reliable)

FAILED_ARTWORKS = [
    {
        "title": "Impression, Sunrise",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1872,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Monet_-_Impression%2C_Sunrise.jpg/640px-Monet_-_Impression%2C_Sunrise.jpg",
        "tags": ["sunrise", "harbor", "boats", "fog", "orange"],
    },
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "style": "Post-Impressionism",
        "year": 1886,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/640px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
        "tags": ["park", "pointillism", "people", "river", "leisure"],
    },
    {
        "title": "Dance at Le Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1876,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg/640px-Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg",
        "tags": ["dance", "party", "garden", "people", "light"],
    },
    {
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1503,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/640px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "tags": ["portrait", "smile", "woman", "landscape", "iconic"],
    },
    {
        "title": "Girl with a Pearl Earring",
        "artist": "Johannes Vermeer",
        "style": "Baroque",
        "year": 1665,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/640px-1665_Girl_with_a_Pearl_Earring.jpg",
        "tags": ["portrait", "pearl", "girl", "turban", "earring"],
    },
    {
        "title": "Cafe Terrace at Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg/640px-Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg",
        "tags": ["cafe", "night", "stars", "yellow", "street"],
    },
    {
        "title": "Sunflowers",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Vincent_Willem_van_Gogh_127.jpg/640px-Vincent_Willem_van_Gogh_127.jpg",
        "tags": ["sunflowers", "vase", "yellow", "still life", "flowers"],
    },
    {
        "title": "Self-Portrait with Bandaged Ear",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1889,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Vincent_Willem_van_Gogh_-_Self-Portrait_with_Bandaged_Ear_%28Courtauld_Institute%29.jpg/640px-Vincent_Willem_van_Gogh_-_Self-Portrait_with_Bandaged_Ear_%28Courtauld_Institute%29.jpg",
        "tags": ["self-portrait", "bandage", "ear", "face", "coat"],
    },
    {
        "title": "The Scream",
        "artist": "Edvard Munch",
        "style": "Expressionism",
        "year": 1893,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/640px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
        "tags": ["scream", "anxiety", "sky", "bridge", "figure"],
    },
    {
        "title": "Liberty Leading the People",
        "artist": "Eugene Delacroix",
        "style": "Romanticism",
        "year": 1830,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg/640px-Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg",
        "tags": ["liberty", "revolution", "flag", "france", "battle"],
    },
    # Fair-use images from /wikipedia/en/ — use original URLs (no /thumb/ support)
    {
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1937,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Guernica.jpg",
        "tags": ["war", "bombing", "pain", "monochrome", "political"],
    },
    {
        "title": "The Elephants",
        "artist": "Salvador Dali",
        "style": "Surrealism",
        "year": 1948,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/1/15/Dali_elephants.jpg",
        "tags": ["elephants", "long legs", "desert", "dreamlike", "surreal"],
    },
    {
        "title": "Composition VIII",
        "artist": "Wassily Kandinsky",
        "style": "Abstract",
        "year": 1923,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/640px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
        "tags": ["geometric", "shapes", "circles", "lines", "colorful"],
    },
    {
        "title": "Broadway Boogie Woogie",
        "artist": "Piet Mondrian",
        "style": "De Stijl",
        "year": 1943,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg/640px-Piet_Mondrian%2C_1942_-_Broadway_Boogie_Woogie.jpg",
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
    {
        "title": "Campbell's Soup Cans",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/9/95/Campbell%27s_Soup_Cans_MOMA_reduced_80%25.jpg",
        "tags": ["soup", "cans", "consumer", "repetition", "commercial"],
    },
    {
        "title": "American Gothic",
        "artist": "Grant Wood",
        "style": "Realism",
        "year": 1930,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/640px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
        "tags": ["couple", "farm", "pitchfork", "rural", "gothic"],
    },
    {
        "title": "Nighthawks",
        "artist": "Edward Hopper",
        "style": "Realism",
        "year": 1942,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Nighthawks_by_Edward_Hopper_1942.jpg/640px-Nighthawks_by_Edward_Hopper_1942.jpg",
        "tags": ["diner", "night", "urban", "loneliness", "city"],
    },
]


MAX_RETRIES = 3
BASE_DELAY = 10           # 10 seconds between each artwork
RETRY_BACKOFF = [15, 30, 60]  # much longer backoff for retry


def ingest_with_retry(art: dict) -> bool:
    """Attempt to ingest an artwork with retry on rate-limit."""
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
                return False

        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < MAX_RETRIES:
                print(f"         [RATE-LIMITED] Will retry...")
                continue
            else:
                print(f"         [FAIL] Error: {err_str[:150]}")
                return False

    return False


def main():
    ensure_collection_exists()

    total = len(FAILED_ARTWORKS)
    success = 0
    failed = 0
    skipped = []

    print(f"\n{'='*60}")
    print(f"  Retrying {total} failed artworks")
    print(f"  ({BASE_DELAY}s delay between requests)")
    print(f"{'='*60}\n")

    for i, art in enumerate(FAILED_ARTWORKS, 1):
        print(f"[{i}/{total}] {art['title']} by {art['artist']}...")

        if ingest_with_retry(art):
            success += 1
        else:
            failed += 1
            skipped.append(art["title"])

        if i < total:
            print(f"         --- waiting {BASE_DELAY}s ---")
            time.sleep(BASE_DELAY)

    print(f"\n{'='*60}")
    print(f"  Retry complete!")
    print(f"  Success: {success}/{total}")
    print(f"  Failed:  {failed}/{total}")
    if skipped:
        print(f"  Still failed: {', '.join(skipped)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
