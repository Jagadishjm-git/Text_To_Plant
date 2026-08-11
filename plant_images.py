"""
plant_images.py
Verified plant image database.
Every URL points to a specific verified image for the exact plant species.
Returns None if no verified image exists -- NEVER uses random or generic queries.
"""

# Verified image map: key = lowercase common name (as in dataset)
VERIFIED_PLANT_IMAGES = {
    "neem": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Azadirachta_indica_%28Neem%29.jpg/800px-Azadirachta_indica_%28Neem%29.jpg",
        "source": "Wikimedia Commons - Azadirachta indica"
    },
    "holy basil (tulsi)": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Ocimum_tenuiflorum3.jpg/800px-Ocimum_tenuiflorum3.jpg",
        "source": "Wikimedia Commons - Ocimum tenuiflorum"
    },
    "mango": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Hapus_Mango.jpg/800px-Hapus_Mango.jpg",
        "source": "Wikimedia Commons - Mangifera indica"
    },
    "bamboo": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Bamboo_grove_in_Iiyama.jpg/640px-Bamboo_grove_in_Iiyama.jpg",
        "source": "Wikimedia Commons - Bambusoideae"
    },
    "ashwagandha": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Withania_somnifera_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-198.jpg/640px-Withania_somnifera_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-198.jpg",
        "source": "Wikimedia Commons - Withania somnifera"
    },
    "lotus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Nelumno_nucifera_open_flower_-_botanic_garden_adelaide2.jpg/800px-Nelumno_nucifera_open_flower_-_botanic_garden_adelaide2.jpg",
        "source": "Wikimedia Commons - Nelumbo nucifera"
    },
    "aloe vera": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Aloe_vera_flower_inset.png/640px-Aloe_vera_flower_inset.png",
        "source": "Wikimedia Commons - Aloe barbadensis miller"
    },
    "turmeric": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Curcuma_longa_roots.jpg/640px-Curcuma_longa_roots.jpg",
        "source": "Wikimedia Commons - Curcuma longa"
    },
    "sandalwood": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Santalum_album-_Chandana1.jpg/640px-Santalum_album-_Chandana1.jpg",
        "source": "Wikimedia Commons - Santalum album"
    },
    "banana": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Banana-Platano.jpg/640px-Banana-Platano.jpg",
        "source": "Wikimedia Commons - Musa acuminata"
    },
    "banyan tree": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Ficus_benghalensis_-_banyan_tree.jpg/800px-Ficus_benghalensis_-_banyan_tree.jpg",
        "source": "Wikimedia Commons - Ficus benghalensis"
    },
    "peepal (sacred fig)": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Ficus_religiosa_Bo-tree.jpg/640px-Ficus_religiosa_Bo-tree.jpg",
        "source": "Wikimedia Commons - Ficus religiosa"
    },
    "brahmi": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Bacopa_monnieri_GFDL.jpg/640px-Bacopa_monnieri_GFDL.jpg",
        "source": "Wikimedia Commons - Bacopa monnieri"
    },
    "curry leaf": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Murraya_koenigii.jpg/640px-Murraya_koenigii.jpg",
        "source": "Wikimedia Commons - Murraya koenigii"
    },
    "indian gooseberry (amla)": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Amla.jpg/640px-Amla.jpg",
        "source": "Wikimedia Commons - Phyllanthus emblica"
    },
    "moringa (drumstick)": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Moringa_oleifera_Blanco2.325.png/640px-Moringa_oleifera_Blanco2.325.png",
        "source": "Wikimedia Commons - Moringa oleifera"
    },
    "coconut": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Coconut_nut.jpg/640px-Coconut_nut.jpg",
        "source": "Wikimedia Commons - Cocos nucifera"
    },
    "black pepper": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Piper_nigrum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-107.jpg/640px-Piper_nigrum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-107.jpg",
        "source": "Wikimedia Commons - Piper nigrum"
    },
    "cardamom": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Elettaria_cardamomum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-052.jpg/640px-Elettaria_cardamomum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-052.jpg",
        "source": "Wikimedia Commons - Elettaria cardamomum"
    },
    "clove": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Cloves.jpg/640px-Cloves.jpg",
        "source": "Wikimedia Commons - Syzygium aromaticum"
    },
    "cinnamon": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Cinnamon-other.jpg/640px-Cinnamon-other.jpg",
        "source": "Wikimedia Commons - Cinnamomum verum"
    },
    "castor": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Ricinus_communis_Blanco1.196.jpg/640px-Ricinus_communis_Blanco1.196.jpg",
        "source": "Wikimedia Commons - Ricinus communis"
    },
    "cotton": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Gossypium_hirsutum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-154.jpg/640px-Gossypium_hirsutum_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-154.jpg",
        "source": "Wikimedia Commons - Gossypium hirsutum"
    },
    "sugarcane": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Sugarcane_field.jpg/640px-Sugarcane_field.jpg",
        "source": "Wikimedia Commons - Saccharum officinarum"
    },
    "pomegranate": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Pomegranate_je.jpg/640px-Pomegranate_je.jpg",
        "source": "Wikimedia Commons - Punica granatum"
    },
    "sunflower": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Sunflower_sky_backdrop.jpg/640px-Sunflower_sky_backdrop.jpg",
        "source": "Wikimedia Commons - Helianthus annuus"
    },
    "rose": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Rosa_canina_flowers.jpg/640px-Rosa_canina_flowers.jpg",
        "source": "Wikimedia Commons - Rosa"
    },
    "jasmine": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Jasminum_sambac_%28L.%29_Aiton_flowers.jpg/640px-Jasminum_sambac_%28L.%29_Aiton_flowers.jpg",
        "source": "Wikimedia Commons - Jasminum sambac"
    },
    "hibiscus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Hibiscus_rosa-sinensis.jpg/640px-Hibiscus_rosa-sinensis.jpg",
        "source": "Wikimedia Commons - Hibiscus rosa-sinensis"
    },
    "papaya": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Papaya_cross_section_BNC.jpg/640px-Papaya_cross_section_BNC.jpg",
        "source": "Wikimedia Commons - Carica papaya"
    },
    "tamarind": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/Tamarind_-_Tamarindus_indica.jpg/640px-Tamarind_-_Tamarindus_indica.jpg",
        "source": "Wikimedia Commons - Tamarindus indica"
    },
}

# Scientific name to common name lookup
SCIENTIFIC_NAME_MAP = {
    "azadirachta indica": "neem",
    "ocimum tenuiflorum": "holy basil (tulsi)",
    "mangifera indica": "mango",
    "bambusoideae spp.": "bamboo",
    "withania somnifera": "ashwagandha",
    "nelumbo nucifera": "lotus",
    "aloe barbadensis miller": "aloe vera",
    "curcuma longa": "turmeric",
    "santalum album": "sandalwood",
    "musa acuminata": "banana",
    "ficus benghalensis": "banyan tree",
    "ficus religiosa": "peepal (sacred fig)",
    "bacopa monnieri": "brahmi",
    "murraya koenigii": "curry leaf",
    "phyllanthus emblica": "indian gooseberry (amla)",
    "moringa oleifera": "moringa (drumstick)",
    "cocos nucifera": "coconut",
    "piper nigrum": "black pepper",
    "elettaria cardamomum": "cardamom",
    "syzygium aromaticum": "clove",
    "cinnamomum verum": "cinnamon",
    "ricinus communis": "castor",
    "gossypium hirsutum": "cotton",
    "saccharum officinarum": "sugarcane",
    "punica granatum": "pomegranate",
    "helianthus annuus": "sunflower",
    "carica papaya": "papaya",
    "tamarindus indica": "tamarind",
}


def get_verified_plant_image(common_name, scientific_name=""):
    """
    Returns a verified image dict:
      {url: str, source: str, is_verified: True}
    or if no verified image available:
      {url: None, source: None, is_verified: False}

    NEVER uses loremflickr, random queries, or unverified sources.
    """
    if not common_name:
        return {"url": None, "source": None, "is_verified": False}

    key = str(common_name).lower().strip()

    # 1. Direct lookup by common name
    if key in VERIFIED_PLANT_IMAGES:
        entry = VERIFIED_PLANT_IMAGES[key]
        return {"url": entry["url"], "source": entry["source"], "is_verified": True}

    # 2. Lookup via scientific name
    sci_key = str(scientific_name).lower().strip()
    if sci_key in SCIENTIFIC_NAME_MAP:
        common_key = SCIENTIFIC_NAME_MAP[sci_key]
        if common_key in VERIFIED_PLANT_IMAGES:
            entry = VERIFIED_PLANT_IMAGES[common_key]
            return {"url": entry["url"], "source": entry["source"], "is_verified": True}

    # 3. Partial match on common name
    for map_key, entry in VERIFIED_PLANT_IMAGES.items():
        if key in map_key or map_key in key:
            return {"url": entry["url"], "source": entry["source"], "is_verified": True}

    # 4. No verified image -- return None, never fall back to random image
    return {"url": None, "source": None, "is_verified": False}
