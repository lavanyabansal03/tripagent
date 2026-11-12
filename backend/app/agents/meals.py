"""Meals: make sure each day has a lunch stop.

Without this, a trip with interests like "coffee, nature, culture" never stopped to eat.
Discovery uses these helpers to find restaurants when no interest brought any, and the
planner uses them to put one restaurant per day in the middle of the day.
"""

from typing import Any

# Diets Geoapify can filter on (it reads them from the search words).
SEARCHABLE_DIETS = ("vegetarian", "vegan", "halal", "kosher", "gluten_free")
# Kinds of food stop that are snacks or drinks, not a meal.
NOT_A_MEAL = {"cafe", "coffee", "coffee_shop", "bakery", "bar", "pub", "nightlife", "ice_cream"}


def is_meal_spot(place: dict[str, Any]) -> bool:
    """A place to have lunch: a restaurant, or food that is not just a cafe or bar."""
    labels = [*place.get("categories", []), *place.get("experience_types", [])]
    kinds = {str(label).lower() for label in labels}
    if "restaurant" in kinds:
        return True
    return "food" in kinds and not (kinds & NOT_A_MEAL)


def diet_words(trip: dict[str, Any]) -> list[str]:
    """Diet words to search with, from the trip's dietary list.

    "vegetarian" in the note usually arrives as avoid: ["meat"], so treat that as vegetarian.
    """
    diets = [d for d in trip.get("dietary", []) or [] if d in SEARCHABLE_DIETS]
    avoid = {str(item).lower() for item in trip.get("avoid", []) or []}
    if "meat" in avoid and "vegetarian" not in diets and "vegan" not in diets:
        diets.append("vegetarian")
    return diets
