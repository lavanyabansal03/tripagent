"""A small hand-made list of real Seattle places, used when there are no API keys.

Only safe facts are stored: name, address, approximate map position and kind of place.
Hours, ratings, review counts and prices stay None because we have not checked them.
The ADR-003 spike will replace this with recorded real provider responses.
"""

from typing import NamedTuple

from app.tools.place import Place

SEED_RETRIEVED_AT = "2026-10-13T00:00:00Z"


class _Seed(NamedTuple):
    id: str
    name: str
    address: str
    lat: float
    lng: float
    categories: list[str]
    experience_types: list[str]
    free: bool  # True only when entry is clearly free (parks, viewpoints, public art)


_SEEDS = [
    _Seed(
        "pl_pike_place", "Pike Place Market",
        "85 Pike St, Seattle", 47.6097, -122.3425,
        ["market", "landmark"], ["landmark", "food", "shopping"], True,
    ),
    _Seed(
        "pl_storyville", "Storyville Coffee Pike Place",
        "94 Pike St #34, Seattle", 47.6096, -122.3416,
        ["cafe"], ["cafe", "food"], False,
    ),
    _Seed(
        "pl_starbucks_reserve", "Starbucks Reserve Roastery",
        "1124 Pike St, Seattle", 47.614, -122.328,
        ["cafe", "roastery"], ["cafe", "food"], False,
    ),
    _Seed(
        "pl_elliott_bay", "Elliott Bay Book Company",
        "1521 10th Ave, Seattle", 47.623, -122.3207,
        ["bookstore"], ["shopping", "culture"], False,
    ),
    _Seed(
        "pl_discovery_park", "Discovery Park",
        "3801 Discovery Park Blvd, Seattle", 47.6605, -122.4068,
        ["park", "trail"], ["nature"], True,
    ),
    _Seed(
        "pl_kerry_park", "Kerry Park",
        "211 W Highland Dr, Seattle", 47.6295, -122.3599,
        ["viewpoint"], ["landmark", "nature"], True,
    ),
    _Seed(
        "pl_chihuly", "Chihuly Garden and Glass",
        "305 Harrison St, Seattle", 47.6205, -122.3509,
        ["museum", "gallery"], ["culture"], False,
    ),
    _Seed(
        "pl_mopop", "Museum of Pop Culture",
        "325 5th Ave N, Seattle", 47.6215, -122.3484,
        ["museum"], ["culture"], False,
    ),
    _Seed(
        "pl_space_needle", "Space Needle",
        "400 Broad St, Seattle", 47.6205, -122.3493,
        ["landmark"], ["landmark"], False,
    ),
    _Seed(
        "pl_sculpture_park", "Olympic Sculpture Park",
        "2901 Western Ave, Seattle", 47.6166, -122.3552,
        ["park", "gallery"], ["culture", "nature"], True,
    ),
    _Seed(
        "pl_fremont_troll", "Fremont Troll",
        "N 36th St, Seattle", 47.651, -122.3473,
        ["public-art"], ["landmark"], True,
    ),
    _Seed(
        "pl_gas_works", "Gas Works Park",
        "2101 N Northlake Way, Seattle", 47.6456, -122.3344,
        ["park"], ["nature", "landmark"], True,
    ),
    _Seed(
        "pl_canon", "Canon",
        "928 12th Ave, Seattle", 47.6233, -122.3197,
        ["bar", "cocktails"], ["nightlife"], False,
    ),
    _Seed(
        "pl_needle_and_thread", "Needle & Thread",
        "1100 E Pike St, Seattle", 47.614, -122.3185,
        ["bar", "cocktails"], ["nightlife"], False,
    ),
    _Seed(
        "pl_walrus", "The Walrus and the Carpenter",
        "4743 Ballard Ave NW, Seattle", 47.6687, -122.3847,
        ["restaurant", "seafood"], ["food"], False,
    ),
    _Seed(
        "pl_ballard_locks", "Hiram M. Chittenden Locks",
        "3015 NW 54th St, Seattle", 47.6656, -122.3973,
        ["park", "landmark"], ["nature", "landmark"], True,
    ),
    _Seed(
        "pl_uw_quad", "University of Washington Quad",
        "4069 Spokane Ln, Seattle", 47.6573, -122.3077,
        ["campus", "park"], ["nature", "culture"], True,
    ),
    _Seed(
        "pl_terra_plata", "Terra Plata",
        "1501 Melrose Ave, Seattle", 47.6236, -122.3205,
        ["restaurant"], ["food"], False,
    ),
    _Seed(
        "pl_victrola", "Victrola Coffee Roasters",
        "310 E Pike St, Seattle", 47.614, -122.3207,
        ["cafe"], ["cafe"], False,
    ),
    _Seed(
        "pl_central_library", "Seattle Central Library",
        "1000 4th Ave, Seattle", 47.6062, -122.3324,
        ["library", "architecture"], ["culture", "landmark"], True,
    ),
    _Seed(
        "pl_alki_beach", "Alki Beach Park",
        "1702 Alki Ave SW, Seattle", 47.5796, -122.41,
        ["beach", "park"], ["nature"], True,
    ),
]


def load_seattle_places() -> list[Place]:
    """Turn the seed list into Place objects."""
    places = []
    for seed in _SEEDS:
        known = "explicit"  # we typed these in ourselves
        guess = "default"  # we do not know these, so they stay empty
        places.append(
            Place(
                id=seed.id,
                sources=["seed"],
                name=seed.name,
                categories=seed.categories,
                experience_types=seed.experience_types,
                lat=seed.lat,
                lng=seed.lng,
                address=seed.address,
                # Free places cost exactly 0. Everything else is unknown, never 0.
                cost_basis="free" if seed.free else "unknown",
                est_cost_low=0 if seed.free else None,
                est_cost_high=0 if seed.free else None,
                retrieved_at=SEED_RETRIEVED_AT,
                field_provenance={
                    "name": known,
                    "address": known,
                    "lat": known,
                    "lng": known,
                    "categories": known,
                    "cost_basis": known if seed.free else guess,
                    "hours": guess,
                    "rating": guess,
                    "review_count": guess,
                    "popularity": guess,
                    "price_level": guess,
                    "local_signal": guess,
                },
            )
        )
    return places
