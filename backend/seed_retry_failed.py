# backend/seed_retry_failed.py
# -*- coding: utf-8 -*-
"""
Retry seeding only the artworks that failed in the initial run.
Uses the updated Wikimedia API resolver in clip_encoder.py.
"""
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
from rag.ingestion.ingestor import ingest_artwork
from rag.schemas.models import IngestRequest
from rag.vectorstore.qdrant_client import ensure_collection_exists
from rag.utils.logger import get_logger

logger = get_logger(__name__)

# These are the 68 titles that failed in the initial seed run.
FAILED_TITLES = [
    "The Luncheon of the Boating Party",
    "A Sunday Afternoon on the Island of La Grande Jatte",
    "The Ballet Class",
    "The Starry Night",
    "Cafe Terrace at Night",
    "Sunflowers",
    "Where Do We Come From? What Are We? Where Are We Going?",
    "Mont Sainte-Victoire",
    "The Large Bathers",
    "Mona Lisa",
    "The Birth of Venus",
    "Girl with a Pearl Earring",
    "The Night Watch",
    "The Calling of Saint Matthew",
    "The Fighting Temeraire",
    "Rain, Steam and Speed",
    "The Gleaners",
    "The Stone Breakers",
    "The Scream",
    "Self-Portrait with Cropped Hair",
    "Portrait of Dr. Gachet",
    "Woman III",
    "The Large Blue Horses",
    "Guernica",
    "Man with a Guitar",
    "Dream Caused by the Flight of a Bee",
    "I and the Village",
    "Composition VIII",
    "Number 1A, 1948",
    "Orange, Red, Yellow",
    "Autumn Rhythm",
    "Vir Heroicus Sublimis",
    "Campbell's Soup Cans",
    "Marilyn Diptych",
    "Whaam!",
    "Just What Is It That Makes Today's Homes So Different",
    "Plum Estate, Kameido",
    "Sudden Shower over Shin-Ohashi Bridge",
    "The Kiss",
    "Portrait of Adele Bloch-Bauer I",
    "Job Cigarettes Poster",
    "The Beethoven Frieze",
    "Metropolis Film Poster",
    "Tamara in a Green Bugatti",
    "Decorative Figure on an Ornamental Background",
    "Black Square",
    "Untitled (Stack)",
    "Who's Afraid of Red, Yellow and Blue III",
    "Dynamism of a Dog on a Leash",
    "The City Rises",
    "Abstract Speed + Sound",
    "The Isle of the Dead",
    "Salome Dancing Before Herod",
    "Ophelia",
    "Oath of the Horatii",
    "Psyche Revived by Cupid's Kiss",
    "Balloon Girl",
    "Love is in the Bin",
    "The Swing",
    "Resting Girl",
    "Pilgrimage to Cythera",
    "Big Self-Portrait",
    "Untitled (Cowboy)",
    "Babur Watching Elephants Fight",
    "Hamzanama Folio",
    "Radha and Krishna in a Grove",
    "Beat the Whites with the Red Wedge",
    "Worker and Kolkhoz Woman",
]


def main():
    # Import the full artwork list from seed_100_styles
    from seed_100_styles import ARTWORKS

    # Filter to just the failed ones
    retry_artworks = [a for a in ARTWORKS if a["title"] in FAILED_TITLES]
    print(f"\nRetrying {len(retry_artworks)} failed artworks (with Wikimedia API resolver)...\n")

    ensure_collection_exists()

    success = 0
    still_failed = []

    for i, art in enumerate(retry_artworks, 1):
        print(f"[{i:>3}/{len(retry_artworks)}] {art['style']:<30} '{art['title']}'")

        try:
            req = IngestRequest(**art)
            result = ingest_artwork(req)
            if result.success:
                print(f"         [OK] ID={result.artwork_id}")
                success += 1
            else:
                print(f"         [FAIL] {result.message}")
                still_failed.append(art["title"])
        except Exception as e:
            msg = str(e)
            print(f"         [ERR] {type(e).__name__}: {msg[:120]}")
            still_failed.append(art["title"])

        # Rate limit: 5s between requests
        if i < len(retry_artworks):
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"  Retry complete! {success}/{len(retry_artworks)} succeeded")
    if still_failed:
        print(f"  Still failed ({len(still_failed)}):")
        for t in still_failed:
            print(f"    - {t}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
