# backend/seed_100_styles.py
# -*- coding: utf-8 -*-
import sys, io
# Force UTF-8 stdout so Unicode chars don't crash on Windows cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#
# Flagship seed script - 93 artworks across 20+ art movements.
# Run from the `backend/` directory:
#   .\venv\Scripts\python.exe -m seed_100_styles
#
# Uses the existing ingestion pipeline (BLIP caption -> CLIP embed -> Qdrant upsert).
# Includes retry + exponential backoff for Wikimedia rate limits.

import time
from rag.ingestion.ingestor import ingest_artwork
from rag.schemas.models import IngestRequest
from rag.vectorstore.qdrant_client import ensure_collection_exists
from rag.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# ARTWORK DATASET - 93 artworks across 20+ major movements
# All image URLs point to public-domain Wikimedia Commons thumbnails (640px).
# ---------------------------------------------------------------------------

ARTWORKS = [

    # -- IMPRESSIONISM (6) -----------------------------------------------------
    {
        "title": "Water Lilies",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1906,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg/640px-Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg",
        "tags": ["water", "lilies", "pond", "reflection", "nature"],
    },
    {
        "title": "Impression, Sunrise",
        "artist": "Claude Monet",
        "style": "Impressionism",
        "year": 1872,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Monet_-_Impression%2C_Sunrise.jpg/640px-Monet_-_Impression%2C_Sunrise.jpg",
        "tags": ["sunrise", "harbor", "boats", "fog", "orange light"],
    },
    {
        "title": "Dance at Le Moulin de la Galette",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1876,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg/640px-Pierre-Auguste_Renoir%2C_Le_Moulin_de_la_Galette.jpg",
        "tags": ["dance", "party", "garden", "dappled light", "social"],
    },
    {
        "title": "The Luncheon of the Boating Party",
        "artist": "Pierre-Auguste Renoir",
        "style": "Impressionism",
        "year": 1881,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Auguste_Renoir_-_Luncheon_of_the_Boating_Party_-_Google_Art_Project.jpg/640px-Auguste_Renoir_-_Luncheon_of_the_Boating_Party_-_Google_Art_Project.jpg",
        "tags": ["lunch", "boating", "summer", "social gathering", "river"],
    },
    {
        "title": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "style": "Post-Impressionism",
        "year": 1886,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/640px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
        "tags": ["park", "pointillism", "dotted", "people", "river"],
    },
    {
        "title": "The Ballet Class",
        "artist": "Edgar Degas",
        "style": "Impressionism",
        "year": 1874,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Degas_-_The_Ballet_Class.jpg/640px-Degas_-_The_Ballet_Class.jpg",
        "tags": ["ballet", "dancers", "studio", "movement", "rehearsal"],
    },

    # -- POST-IMPRESSIONISM (6) ------------------------------------------------
    {
        "title": "The Starry Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1889,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/640px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        "tags": ["night", "swirling", "stars", "village", "sky"],
    },
    {
        "title": "Cafe Terrace at Night",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg/640px-Van_Gogh_-_Terrasse_des_Caf%C3%A9s_an_der_Place_du_Forum_in_Arles_am_Abend1.jpg",
        "tags": ["cafe", "night", "yellow", "stars", "cobblestone"],
    },
    {
        "title": "Sunflowers",
        "artist": "Vincent van Gogh",
        "style": "Post-Impressionism",
        "year": 1888,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Vincent_Willem_van_Gogh_127.jpg/640px-Vincent_Willem_van_Gogh_127.jpg",
        "tags": ["sunflowers", "yellow", "vase", "still life", "warm"],
    },
    {
        "title": "Where Do We Come From? What Are We? Where Are We Going?",
        "artist": "Paul Gauguin",
        "style": "Post-Impressionism",
        "year": 1898,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Paul_Gauguin_-_D%27ou_venons-nous.jpg/640px-Paul_Gauguin_-_D%27ou_venons-nous.jpg",
        "tags": ["tropical", "figures", "spiritual", "tahiti", "existential"],
    },
    {
        "title": "Mont Sainte-Victoire",
        "artist": "Paul Cezanne",
        "style": "Post-Impressionism",
        "year": 1904,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Paul_C%C3%A9zanne_-_Mont_Sainte-Victoire_-_Google_Art_Project.jpg/640px-Paul_C%C3%A9zanne_-_Mont_Sainte-Victoire_-_Google_Art_Project.jpg",
        "tags": ["mountain", "landscape", "structured", "geometric", "provence"],
    },
    {
        "title": "The Large Bathers",
        "artist": "Paul Cezanne",
        "style": "Post-Impressionism",
        "year": 1906,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Paul_C%C3%A9zanne_-_The_Large_Bathers_%28Philadelphia%29.jpg/640px-Paul_C%C3%A9zanne_-_The_Large_Bathers_%28Philadelphia%29.jpg",
        "tags": ["figures", "bathing", "trees", "landscape", "geometric"],
    },

    # -- RENAISSANCE (6) -------------------------------------------------------
    {
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1503,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/640px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg",
        "tags": ["portrait", "smile", "woman", "sfumato", "iconic"],
    },
    {
        "title": "The Birth of Venus",
        "artist": "Sandro Botticelli",
        "style": "Renaissance",
        "year": 1485,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/640px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
        "tags": ["venus", "goddess", "shell", "sea", "mythological"],
    },
    {
        "title": "The Creation of Adam",
        "artist": "Michelangelo",
        "style": "Renaissance",
        "year": 1512,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg/640px-Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg",
        "tags": ["god", "adam", "touch", "ceiling", "divine"],
    },
    {
        "title": "The School of Athens",
        "artist": "Raphael",
        "style": "Renaissance",
        "year": 1511,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg/640px-%22The_School_of_Athens%22_by_Raffaello_Sanzio_da_Urbino.jpg",
        "tags": ["philosophy", "scholars", "architecture", "arched", "fresco"],
    },
    {
        "title": "The Last Supper",
        "artist": "Leonardo da Vinci",
        "style": "Renaissance",
        "year": 1498,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/%C3%9Altima_Cena_-_Da_Vinci_5.jpg/640px-%C3%9Altima_Cena_-_Da_Vinci_5.jpg",
        "tags": ["jesus", "disciples", "meal", "dramatic", "biblical"],
    },
    {
        "title": "Primavera",
        "artist": "Sandro Botticelli",
        "style": "Renaissance",
        "year": 1482,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Botticelli-primavera.jpg/640px-Botticelli-primavera.jpg",
        "tags": ["spring", "graces", "mythological", "garden", "allegory"],
    },

    # -- BAROQUE (5) -----------------------------------------------------------
    {
        "title": "Girl with a Pearl Earring",
        "artist": "Johannes Vermeer",
        "style": "Baroque",
        "year": 1665,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/640px-1665_Girl_with_a_Pearl_Earring.jpg",
        "tags": ["portrait", "pearl", "turban", "light", "intimate"],
    },
    {
        "title": "The Night Watch",
        "artist": "Rembrandt",
        "style": "Baroque",
        "year": 1642,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/The_Night_Watch_-_HD.jpg/640px-The_Night_Watch_-_HD.jpg",
        "tags": ["militia", "dramatic lighting", "group", "chiaroscuro", "Dutch"],
    },
    {
        "title": "The Calling of Saint Matthew",
        "artist": "Caravaggio",
        "style": "Baroque",
        "year": 1600,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Caravaggio_-_La_vocazione_di_san_Matteo.jpg/640px-Caravaggio_-_La_vocazione_di_san_Matteo.jpg",
        "tags": ["chiaroscuro", "dramatic", "light", "biblical", "shadow"],
    },
    {
        "title": "The Anatomy Lesson of Dr. Nicolaes Tulp",
        "artist": "Rembrandt",
        "style": "Baroque",
        "year": 1632,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Rembrandt_-_The_Anatomy_Lesson_of_Dr_Nicolaes_Tulp.jpg/640px-Rembrandt_-_The_Anatomy_Lesson_of_Dr_Nicolaes_Tulp.jpg",
        "tags": ["anatomy", "surgery", "group portrait", "dramatic", "Dutch"],
    },
    {
        "title": "Las Meninas",
        "artist": "Diego Velazquez",
        "style": "Baroque",
        "year": 1656,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Las_Meninas_01.jpg/640px-Las_Meninas_01.jpg",
        "tags": ["Spanish court", "princess", "mirror", "complex", "royal"],
    },

    # -- ROMANTICISM (5) -------------------------------------------------------
    {
        "title": "Wanderer above the Sea of Fog",
        "artist": "Caspar David Friedrich",
        "style": "Romanticism",
        "year": 1818,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg/640px-Caspar_David_Friedrich_-_Wanderer_above_the_sea_of_fog.jpg",
        "tags": ["solitude", "mountains", "fog", "sublime", "silhouette"],
    },
    {
        "title": "Liberty Leading the People",
        "artist": "Eugene Delacroix",
        "style": "Romanticism",
        "year": 1830,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg/640px-Eug%C3%A8ne_Delacroix_-_Le_28_Juillet._La_Libert%C3%A9_guidant_le_peuple.jpg",
        "tags": ["revolution", "flag", "allegory", "battle", "freedom"],
    },
    {
        "title": "The Fighting Temeraire",
        "artist": "J.M.W. Turner",
        "style": "Romanticism",
        "year": 1839,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/The_Fighting_Temeraire%2C_JMW_Turner%2C_National_Gallery.jpg/640px-The_Fighting_Temeraire%2C_JMW_Turner%2C_National_Gallery.jpg",
        "tags": ["ship", "sunset", "steam", "sea", "nostalgia"],
    },
    {
        "title": "Rain, Steam and Speed",
        "artist": "J.M.W. Turner",
        "style": "Romanticism",
        "year": 1844,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Turner_-_Rain%2C_Steam_and_Speed_-_National_Gallery_file.jpg/640px-Turner_-_Rain%2C_Steam_and_Speed_-_National_Gallery_file.jpg",
        "tags": ["train", "speed", "atmospheric", "industrial", "bridge"],
    },
    {
        "title": "Saturn Devouring His Son",
        "artist": "Francisco Goya",
        "style": "Romanticism",
        "year": 1823,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Francisco_de_Goya%2C_Saturno_devorando_a_su_hijo_%281819-1823%29.jpg/640px-Francisco_de_Goya%2C_Saturno_devorando_a_su_hijo_%281819-1823%29.jpg",
        "tags": ["dark", "horror", "mythological", "savage", "intense"],
    },

    # -- REALISM (4) -----------------------------------------------------------
    {
        "title": "American Gothic",
        "artist": "Grant Wood",
        "style": "Realism",
        "year": 1930,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/640px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
        "tags": ["rural", "farm", "couple", "pitchfork", "americana"],
    },
    {
        "title": "Nighthawks",
        "artist": "Edward Hopper",
        "style": "Realism",
        "year": 1942,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Nighthawks_by_Edward_Hopper_1942.jpg/640px-Nighthawks_by_Edward_Hopper_1942.jpg",
        "tags": ["diner", "night", "urban", "loneliness", "neon"],
    },
    {
        "title": "The Gleaners",
        "artist": "Jean-Francois Millet",
        "style": "Realism",
        "year": 1857,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Jean-Fran%C3%A7ois_Millet_-_Gleaners_-_Google_Art_Project_2.jpg/640px-Jean-Fran%C3%A7ois_Millet_-_Gleaners_-_Google_Art_Project_2.jpg",
        "tags": ["peasants", "harvest", "field", "labor", "countryside"],
    },
    {
        "title": "The Stone Breakers",
        "artist": "Gustave Courbet",
        "style": "Realism",
        "year": 1849,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Courbet_-_stone-breakers.jpg/640px-Courbet_-_stone-breakers.jpg",
        "tags": ["labor", "workers", "social", "road", "rough"],
    },

    # -- EXPRESSIONISM (5) -----------------------------------------------------
    {
        "title": "The Scream",
        "artist": "Edvard Munch",
        "style": "Expressionism",
        "year": 1893,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/640px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
        "tags": ["anguish", "sky", "wavy", "bridge", "figure"],
    },
    {
        "title": "Self-Portrait with Cropped Hair",
        "artist": "Frida Kahlo",
        "style": "Expressionism",
        "year": 1940,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/a/a2/Frida_Kahlo%2C_1940%2C_Self-portrait_with_Cropped_Hair.jpg",
        "tags": ["self-portrait", "identity", "hair", "scissors", "powerful"],
    },
    {
        "title": "Portrait of Dr. Gachet",
        "artist": "Vincent van Gogh",
        "style": "Expressionism",
        "year": 1890,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Van_Gogh_-_Portrait_of_Dr._Gachet.jpg/640px-Van_Gogh_-_Portrait_of_Dr._Gachet.jpg",
        "tags": ["portrait", "melancholy", "doctor", "foxglove", "emotional"],
    },
    {
        "title": "Woman III",
        "artist": "Willem de Kooning",
        "style": "Abstract Expressionism",
        "year": 1953,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/8/8b/De_Kooning_-_Woman_III.jpg",
        "tags": ["abstract", "figure", "aggressive", "gestural", "woman"],
    },
    {
        "title": "The Large Blue Horses",
        "artist": "Franz Marc",
        "style": "Expressionism",
        "year": 1911,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Franz_Marc_-_The_Large_Blue_Horses_-_Google_Art_Project.jpg/640px-Franz_Marc_-_The_Large_Blue_Horses_-_Google_Art_Project.jpg",
        "tags": ["blue", "horses", "animals", "vivid", "emotional"],
    },

    # -- CUBISM (4) ------------------------------------------------------------
    {
        "title": "Guernica",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1937,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Guernica.jpg",
        "tags": ["war", "monochrome", "fragmented", "suffering", "political"],
    },
    {
        "title": "Les Demoiselles d'Avignon",
        "artist": "Pablo Picasso",
        "style": "Cubism",
        "year": 1907,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/4/4c/Les_Demoiselles_d%27Avignon.jpg",
        "tags": ["angular", "African masks", "deconstructed", "female", "proto-cubist"],
    },
    {
        "title": "Nude Descending a Staircase",
        "artist": "Marcel Duchamp",
        "style": "Cubism",
        "year": 1912,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/c/c0/Duchamp_-_Nude_Descending_a_Staircase.jpg",
        "tags": ["motion", "mechanical", "fragmented", "figure", "futurist"],
    },
    {
        "title": "Man with a Guitar",
        "artist": "Georges Braque",
        "style": "Cubism",
        "year": 1911,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Georges_Braque%2C_1911-12%2C_Man_with_a_Guitar%2C_oil_on_canvas%2C_116.2_x_80.9_cm%2C_Museum_of_Modern_Art%2C_New_York.jpg/640px-Georges_Braque%2C_1911-12%2C_Man_with_a_Guitar%2C_oil_on_canvas%2C_116.2_x_80.9_cm%2C_Museum_of_Modern_Art%2C_New_York.jpg",
        "tags": ["analytic cubism", "monochrome", "fractured", "guitar", "planes"],
    },

    # -- SURREALISM (5) --------------------------------------------------------
    {
        "title": "The Persistence of Memory",
        "artist": "Salvador Dali",
        "style": "Surrealism",
        "year": 1931,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg",
        "tags": ["melting clocks", "desert", "dreamlike", "time", "distorted"],
    },
    {
        "title": "The Son of Man",
        "artist": "Rene Magritte",
        "style": "Surrealism",
        "year": 1964,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/e/e5/Magritte_TheSonOfMan.jpg",
        "tags": ["apple", "bowler hat", "mystery", "concealment", "man"],
    },
    {
        "title": "The Treachery of Images",
        "artist": "Rene Magritte",
        "style": "Surrealism",
        "year": 1929,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/b/b9/MagrittePipe.jpg",
        "tags": ["pipe", "text", "conceptual", "philosophical", "iconic"],
    },
    {
        "title": "Dream Caused by the Flight of a Bee",
        "artist": "Salvador Dali",
        "style": "Surrealism",
        "year": 1944,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/4/40/DreamsCausedByTheFlightOfABeeSurroundingAPomegranateASecondBeforeAwakening.JPG",
        "tags": ["tiger", "fish", "elephant", "dream", "bizarre"],
    },
    {
        "title": "I and the Village",
        "artist": "Marc Chagall",
        "style": "Surrealism",
        "year": 1911,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/0/0c/I_and_the_Village.jpg",
        "tags": ["village", "goat", "folklore", "dreamlike", "colorful"],
    },

    # -- ABSTRACT & ABSTRACT EXPRESSIONISM (6) ---------------------------------
    {
        "title": "Composition VIII",
        "artist": "Wassily Kandinsky",
        "style": "Abstract",
        "year": 1923,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/640px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
        "tags": ["geometric", "circles", "lines", "colorful", "musical"],
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
        "tags": ["drip painting", "splatter", "chaotic", "action painting", "raw"],
    },
    {
        "title": "Orange, Red, Yellow",
        "artist": "Mark Rothko",
        "style": "Abstract Expressionism",
        "year": 1961,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/b/bd/Mark_Rothko_-_Orange%2C_Red%2C_Yellow_%281961%29.jpg",
        "tags": ["color field", "luminous", "warm", "contemplative", "large"],
    },
    {
        "title": "Autumn Rhythm",
        "artist": "Jackson Pollock",
        "style": "Abstract Expressionism",
        "year": 1950,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/4/4a/No._30%2C_1950.jpg",
        "tags": ["drip", "black white", "gestural", "rhythmic", "large scale"],
    },
    {
        "title": "Vir Heroicus Sublimis",
        "artist": "Barnett Newman",
        "style": "Abstract Expressionism",
        "year": 1950,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Barnett_Newman%2C_1950-51%2C_Vir_Heroicus_Sublimis.jpg",
        "tags": ["red", "color field", "zip", "monumental", "minimal"],
    },

    # -- POP ART (4) -----------------------------------------------------------
    {
        "title": "Campbell's Soup Cans",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/9/95/Campbell%27s_Soup_Cans_MOMA_reduced_80%25.jpg",
        "tags": ["consumer", "repetition", "commercial", "cans", "bold"],
    },
    {
        "title": "Marilyn Diptych",
        "artist": "Andy Warhol",
        "style": "Pop Art",
        "year": 1962,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/b/b2/Warhol-Monroe.jpg",
        "tags": ["celebrity", "silk screen", "repetition", "Marilyn Monroe", "faded"],
    },
    {
        "title": "Whaam!",
        "artist": "Roy Lichtenstein",
        "style": "Pop Art",
        "year": 1963,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/2/29/Roy_Lichtenstein_Whaam.jpg",
        "tags": ["comic", "bold lines", "war", "fighter jet", "benday dots"],
    },
    {
        "title": "Just What Is It That Makes Today's Homes So Different",
        "artist": "Richard Hamilton",
        "style": "Pop Art",
        "year": 1956,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/9/9d/Hamilton-appealing2.jpg",
        "tags": ["collage", "consumer culture", "bodybuilder", "pop icons", "interior"],
    },

    # -- UKIYO-E & JAPANESE (4) ------------------------------------------------
    {
        "title": "The Great Wave off Kanagawa",
        "artist": "Katsushika Hokusai",
        "style": "Ukiyo-e",
        "year": 1831,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/640px-Tsunami_by_hokusai_19th_century.jpg",
        "tags": ["wave", "ocean", "Japan", "Mount Fuji", "woodblock"],
    },
    {
        "title": "Plum Estate, Kameido",
        "artist": "Utagawa Hiroshige",
        "style": "Ukiyo-e",
        "year": 1857,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Hiroshige_PlumEstate.jpg/640px-Hiroshige_PlumEstate.jpg",
        "tags": ["plum blossoms", "branches", "garden", "Japan", "spring"],
    },
    {
        "title": "Sudden Shower over Shin-Ohashi Bridge",
        "artist": "Utagawa Hiroshige",
        "style": "Ukiyo-e",
        "year": 1857,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Hiroshige_Ohashi_Atake.jpg/640px-Hiroshige_Ohashi_Atake.jpg",
        "tags": ["rain", "bridge", "woodblock", "Japan", "storm"],
    },
    {
        "title": "Fine Wind, Clear Morning",
        "artist": "Katsushika Hokusai",
        "style": "Ukiyo-e",
        "year": 1830,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Red_Fuji_southern_wind_clear_morning.jpg/640px-Red_Fuji_southern_wind_clear_morning.jpg",
        "tags": ["Mount Fuji", "red", "sky", "Japan", "woodblock"],
    },

    # -- ART NOUVEAU (4) -------------------------------------------------------
    {
        "title": "The Kiss",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1908,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/The_Kiss_-_Gustav_Klimt_-_Google_Cultural_Institute.jpg/640px-The_Kiss_-_Gustav_Klimt_-_Google_Cultural_Institute.jpg",
        "tags": ["gold", "embrace", "lovers", "ornate", "tender"],
    },
    {
        "title": "Portrait of Adele Bloch-Bauer I",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1907,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Klimt_-_Adele_Bloch-Bauer_I.jpg/640px-Klimt_-_Adele_Bloch-Bauer_I.jpg",
        "tags": ["gold", "ornate", "woman", "geometric", "luxury"],
    },
    {
        "title": "Job Cigarettes Poster",
        "artist": "Alphonse Mucha",
        "style": "Art Nouveau",
        "year": 1896,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Alphonse_Mucha_-_Job_Cigarettes_-_1896.jpg/640px-Alphonse_Mucha_-_Job_Cigarettes_-_1896.jpg",
        "tags": ["poster", "woman", "decorative border", "flowing hair", "ornate"],
    },
    {
        "title": "The Beethoven Frieze",
        "artist": "Gustav Klimt",
        "style": "Art Nouveau",
        "year": 1902,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Klimt_Beethovenfries_1.jpg/640px-Klimt_Beethovenfries_1.jpg",
        "tags": ["frieze", "symbolist", "longing", "gold", "figures"],
    },

    # -- ART DECO (3) ----------------------------------------------------------
    {
        "title": "Metropolis Film Poster",
        "artist": "Heinz Schulz-Neudamm",
        "style": "Art Deco",
        "year": 1927,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Metropolis_%281927_film_poster%29.jpg/640px-Metropolis_%281927_film_poster%29.jpg",
        "tags": ["poster", "robot", "city", "geometric", "futuristic"],
    },
    {
        "title": "Tamara in a Green Bugatti",
        "artist": "Tamara de Lempicka",
        "style": "Art Deco",
        "year": 1929,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/c/c5/Tamara_de_Lempicka_%281929%29.jpg",
        "tags": ["driver", "glamorous", "car", "sleek", "bold colors"],
    },
    {
        "title": "Decorative Figure on an Ornamental Background",
        "artist": "Henri Matisse",
        "style": "Art Deco",
        "year": 1925,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/b/ba/Decorative_Figure_on_an_Ornamental_Ground_by_Henri_Matisse.jpg",
        "tags": ["pattern", "flat", "decorative", "figure", "bold"],
    },

    # -- MINIMALISM (3) --------------------------------------------------------
    {
        "title": "Black Square",
        "artist": "Kazimir Malevich",
        "style": "Suprematism",
        "year": 1915,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/f/f5/Malevich_black_square.jpg",
        "tags": ["black", "square", "conceptual", "suprematist", "void"],
    },
    {
        "title": "Untitled (Stack)",
        "artist": "Donald Judd",
        "style": "Minimalism",
        "year": 1967,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/1/10/Untitled_stack_Judd.jpg",
        "tags": ["stack", "metal", "sculpture", "repetition", "industrial"],
    },
    {
        "title": "Who's Afraid of Red, Yellow and Blue III",
        "artist": "Barnett Newman",
        "style": "Minimalism",
        "year": 1967,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/0/0e/Barnett_Newman_-_Whos_Afraid_of_Red%2C_Yellow_and_Blue_III.jpg",
        "tags": ["color field", "large scale", "bold", "primary colors", "zip"],
    },

    # -- FUTURISM (3) ----------------------------------------------------------
    {
        "title": "Dynamism of a Dog on a Leash",
        "artist": "Giacomo Balla",
        "style": "Futurism",
        "year": 1912,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/1/1a/Giacomo_Balla%2C_1912%2C_Dynamism_of_a_Dog_on_a_Leash.jpg",
        "tags": ["motion blur", "dog", "movement", "repetition", "speed"],
    },
    {
        "title": "The City Rises",
        "artist": "Umberto Boccioni",
        "style": "Futurism",
        "year": 1910,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Umberto_Boccioni_005.jpg/640px-Umberto_Boccioni_005.jpg",
        "tags": ["horses", "labor", "movement", "modern city", "energy"],
    },
    {
        "title": "Abstract Speed + Sound",
        "artist": "Giacomo Balla",
        "style": "Futurism",
        "year": 1913,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Giacomo_Balla%2C_1913-14%2C_Abstract_Speed_%2B_Sound%2C_oil_on_cardboard%2C_54.5_x_76.5_cm%2C_Peggy_Guggenheim_Collection%2C_Venice.jpg/640px-Giacomo_Balla%2C_1913-14%2C_Abstract_Speed_%2B_Sound%2C_oil_on_cardboard%2C_54.5_x_76.5_cm%2C_Peggy_Guggenheim_Collection%2C_Venice.jpg",
        "tags": ["speed", "sound", "abstraction", "dynamic", "colorful"],
    },

    # -- SYMBOLISM (3) ---------------------------------------------------------
    {
        "title": "The Isle of the Dead",
        "artist": "Arnold Bocklin",
        "style": "Symbolism",
        "year": 1883,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/B%C3%B6cklin%2C_arnold%2C_die_toteninsel%2C_dritte_fassung%2C_%C3%B6l_auf_holz%2C_1883%2C_80x150cm.jpg/640px-B%C3%B6cklin%2C_arnold%2C_die_toteninsel%2C_dritte_fassung%2C_%C3%B6l_auf_holz%2C_1883%2C_80x150cm.jpg",
        "tags": ["island", "death", "dark", "trees", "mysterious"],
    },
    {
        "title": "Salome Dancing Before Herod",
        "artist": "Gustave Moreau",
        "style": "Symbolism",
        "year": 1876,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Gustave_Moreau_-_Salome_Dancing_Before_Herod_-_Hammer_Museum.jpg/640px-Gustave_Moreau_-_Salome_Dancing_Before_Herod_-_Hammer_Museum.jpg",
        "tags": ["biblical", "exotic", "jeweled", "dark", "ornate"],
    },
    {
        "title": "Ophelia",
        "artist": "John Everett Millais",
        "style": "Symbolism",
        "year": 1852,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/John_Everett_Millais_-_Ophelia_-_Google_Art_Project.jpg/640px-John_Everett_Millais_-_Ophelia_-_Google_Art_Project.jpg",
        "tags": ["water", "flowers", "drowning", "Pre-Raphaelite", "woman"],
    },

    # -- NEOCLASSICISM (3) -----------------------------------------------------
    {
        "title": "Napoleon Crossing the Alps",
        "artist": "Jacques-Louis David",
        "style": "Neoclassicism",
        "year": 1801,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/David_-_Napoleon_crossing_the_Alps_-_Malmaison2.jpg/640px-David_-_Napoleon_crossing_the_Alps_-_Malmaison2.jpg",
        "tags": ["Napoleon", "horse", "heroic", "dramatic", "mountain"],
    },
    {
        "title": "Oath of the Horatii",
        "artist": "Jacques-Louis David",
        "style": "Neoclassicism",
        "year": 1784,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Jacques-Louis_David_-_Oath_of_the_Horatii_-_Google_Art_Project.jpg/640px-Jacques-Louis_David_-_Oath_of_the_Horatii_-_Google_Art_Project.jpg",
        "tags": ["swords", "soldiers", "honor", "Roman", "patriotism"],
    },
    {
        "title": "Psyche Revived by Cupid's Kiss",
        "artist": "Antonio Canova",
        "style": "Neoclassicism",
        "year": 1787,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Psyche_revived_Louvre_MR1777.jpg/640px-Psyche_revived_Louvre_MR1777.jpg",
        "tags": ["sculpture", "marble", "love", "mythology", "tender"],
    },

    # -- STREET ART (3) --------------------------------------------------------
    {
        "title": "Balloon Girl",
        "artist": "Banksy",
        "style": "Street Art",
        "year": 2002,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Banksy_-_Balloon_Girl_%282006%29.jpg/640px-Banksy_-_Balloon_Girl_%282006%29.jpg",
        "tags": ["stencil", "girl", "balloon", "hope", "urban"],
    },
    {
        "title": "Love is in the Bin",
        "artist": "Banksy",
        "style": "Street Art",
        "year": 2018,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Banksy_-_Girl_With_Balloon_%28Shred_the_Love%29.jpg/640px-Banksy_-_Girl_With_Balloon_%28Shred_the_Love%29.jpg",
        "tags": ["shredded", "auction", "stencil", "conceptual", "provocative"],
    },
    {
        "title": "We Can Do It",
        "artist": "J. Howard Miller",
        "style": "Propaganda Poster",
        "year": 1943,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/We_Can_Do_It%21.jpg/640px-We_Can_Do_It%21.jpg",
        "tags": ["poster", "woman", "bold", "patriotic", "iconic"],
    },

    # -- ROCOCO (3) ------------------------------------------------------------
    {
        "title": "The Swing",
        "artist": "Jean-Honore Fragonard",
        "style": "Rococo",
        "year": 1767,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Fragonard%2C_The_Swing.jpg/640px-Fragonard%2C_The_Swing.jpg",
        "tags": ["swing", "garden", "playful", "pastel", "flirtatious"],
    },
    {
        "title": "Resting Girl",
        "artist": "Francois Boucher",
        "style": "Rococo",
        "year": 1752,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Fran%C3%A7ois_Boucher_-_Resting_Girl_%28Louise_O%27Murphy%29_-_Google_Art_Project.jpg/640px-Fran%C3%A7ois_Boucher_-_Resting_Girl_%28Louise_O%27Murphy%29_-_Google_Art_Project.jpg",
        "tags": ["nude", "pastel", "reclining", "soft", "intimate"],
    },
    {
        "title": "Pilgrimage to Cythera",
        "artist": "Antoine Watteau",
        "style": "Rococo",
        "year": 1717,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Watteau_-_Pilgrimage_to_Cythera%2C_Louvre.JPG/640px-Watteau_-_Pilgrimage_to_Cythera%2C_Louvre.JPG",
        "tags": ["pastoral", "lovers", "island", "mythological", "elegant"],
    },

    # -- PHOTOREALISM (2) ------------------------------------------------------
    {
        "title": "Big Self-Portrait",
        "artist": "Chuck Close",
        "style": "Photorealism",
        "year": 1967,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/4/4c/CloseChuckBigSP1967-68.jpg",
        "tags": ["portrait", "gridded", "photographic", "extreme detail", "face"],
    },
    {
        "title": "Untitled (Cowboy)",
        "artist": "Richard Prince",
        "style": "Appropriation Art",
        "year": 1989,
        "image_url": "https://upload.wikimedia.org/wikipedia/en/e/e4/Richard_Prince_Untitled_%28Cowboy%29_1980-1992.jpg",
        "tags": ["cowboy", "appropriation", "photography", "American west", "bold"],
    },

    # -- MUGHAL & INDIAN (3) ---------------------------------------------------
    {
        "title": "Babur Watching Elephants Fight",
        "artist": "Unknown Mughal",
        "style": "Mughal Miniature",
        "year": 1590,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Babur_watches_as_two_elephants_fight%2C_Baburnama.jpg/640px-Babur_watches_as_two_elephants_fight%2C_Baburnama.jpg",
        "tags": ["elephants", "emperor", "detailed", "miniature", "Mughal"],
    },
    {
        "title": "Hamzanama Folio",
        "artist": "Mir Sayyid Ali",
        "style": "Mughal Miniature",
        "year": 1562,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Hamzanama_folio.jpg/640px-Hamzanama_folio.jpg",
        "tags": ["miniature", "narrative", "intricate", "vibrant", "Persian"],
    },
    {
        "title": "Radha and Krishna in a Grove",
        "artist": "Unknown Rajasthani",
        "style": "Indian Classical",
        "year": 1720,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Radha_and_Krishna_in_a_Grove%2C_Rajasthan%2C_Bundi%2C_c1720.jpg/640px-Radha_and_Krishna_in_a_Grove%2C_Rajasthan%2C_Bundi%2C_c1720.jpg",
        "tags": ["Radha", "Krishna", "Rajasthani", "vibrant", "devotional"],
    },

    # -- CONSTRUCTIVISM (2) ----------------------------------------------------
    {
        "title": "Beat the Whites with the Red Wedge",
        "artist": "El Lissitzky",
        "style": "Constructivism",
        "year": 1919,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/El_Lissitzky_-_Beat_the_Whites_with_the_Red_Wedge_%281919%29.jpg/640px-El_Lissitzky_-_Beat_the_Whites_with_the_Red_Wedge_%281919%29.jpg",
        "tags": ["red", "wedge", "geometric", "propaganda", "bold"],
    },
    {
        "title": "Worker and Kolkhoz Woman",
        "artist": "Vera Mukhina",
        "style": "Constructivism",
        "year": 1937,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Vera_Mukhina_%281889-1953%29%2C_Worker_and_Kolkhoz_Woman%2C_1937.jpg/640px-Vera_Mukhina_%281889-1953%29%2C_Worker_and_Kolkhoz_Woman%2C_1937.jpg",
        "tags": ["sculpture", "workers", "socialist", "monumental", "dynamic"],
    },

]


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
BASE_DELAY = 5              # seconds between artworks (Wikimedia rate limit)
RETRY_BACKOFF = [10, 30, 60] # seconds for 1st / 2nd / 3rd retry


def ingest_with_retry(art: dict, index: int, total: int) -> bool:
    """Attempt to ingest an artwork, retrying on transient errors."""
    title = art["title"]

    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"         [RETRY {attempt}/{MAX_RETRIES}] Waiting {wait}s ...")
                time.sleep(wait)

            req = IngestRequest(**art)
            result = ingest_artwork(req)

            if result.success:
                print(f"         [OK] ID={result.artwork_id}")
                return True
            else:
                print(f"         [FAIL] {result.message}")

        except Exception as exc:
            msg = str(exc)
            is_rate_limit = "429" in msg or "Too Many Requests" in msg.lower()
            is_not_found  = "404" in msg or "Not Found" in msg
            is_bad_size   = "400" in msg or "thumbnail sizes" in msg.lower()

            if is_not_found or is_bad_size:
                print(f"         [SKIP] {exc.__class__.__name__}: {msg[:100]}")
                return False
            elif is_rate_limit and attempt < MAX_RETRIES:
                print(f"         [429] Rate limited, will retry ...")
                continue
            else:
                print(f"         [ERR] [{exc.__class__.__name__}] {msg[:120]}")
                return False

    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_collection_exists()

    total = len(ARTWORKS)
    success_count = 0
    failed_titles: list[str] = []

    print(f"\n{'='*64}")
    print(f"  RGStudio - Seeding {total} artworks into Qdrant")
    print(f"  Movements: Impressionism, Renaissance, Baroque, Cubism,")
    print(f"             Surrealism, Abstract, Pop Art, Ukiyo-e + 12 more")
    print(f"  Delay: {BASE_DELAY}s between requests  |  Up to {MAX_RETRIES} retries")
    print(f"{'='*64}\n")

    for i, art in enumerate(ARTWORKS, 1):
        print(f"[{i:>3}/{total}] {art['style']:<30} '{art['title']}' by {art['artist']}")

        ok = ingest_with_retry(art, i, total)
        if ok:
            success_count += 1
        else:
            failed_titles.append(art["title"])

        # Respect Wikimedia rate limits between artworks
        if i < total:
            time.sleep(BASE_DELAY)

    print(f"\n{'='*64}")
    print(f"  Seeding complete!")
    print(f"  Success : {success_count}/{total}")
    print(f"  Failed  : {len(failed_titles)}/{total}")
    if failed_titles:
        print(f"\n  Failed artworks:")
        for t in failed_titles:
            print(f"    - {t}")
    print(f"{'='*64}\n")

    if failed_titles:
        print("[WARN] Some artworks failed. Check logs above.")


if __name__ == "__main__":
    main()
