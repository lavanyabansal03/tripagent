"""Lunch stops and pace: days should not end at 2 PM with no meal."""

from app.agents.discovery import discover_places
from app.agents.meals import diet_words, is_meal_spot
from app.agents.planner import LUNCH_SLOT, plan_and_validate
from app.tools.mock_places import MockPlaceSearch


def place(name: str, kinds: list[str], experience: list[str], lat: float, lng: float) -> dict:
    return {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "categories": kinds,
        "experience_types": experience,
        "lat": lat,
        "lng": lng,
        "sources": ["seed"],
    }


def test_restaurants_are_meals_but_cafes_and_bars_are_not():
    assert is_meal_spot(place("Tulio", ["restaurant"], ["food"], 47.6, -122.3))
    assert not is_meal_spot(place("Retro Coffee", ["cafe"], ["cafe", "food"], 47.6, -122.3))
    assert not is_meal_spot(place("Canon", ["bar"], ["nightlife", "food"], 47.6, -122.3))
    assert not is_meal_spot(place("Freeway Park", ["park"], ["nature"], 47.6, -122.3))


def test_vegetarian_comes_from_dietary_or_avoiding_meat():
    assert diet_words({"dietary": ["vegan"]}) == ["vegan"]
    assert diet_words({"avoid": ["meat"]}) == ["vegetarian"]
    assert diet_words({"dietary": ["nut_allergy"]}) == []  # not something we can search for


def test_lunch_search_asks_for_vegetarian_first():
    queries: list[str] = []

    class Recording:
        def search_places(self, **kwargs):
            queries.append(kwargs["query"])
            return MockPlaceSearch().search_places(**kwargs)

    trip = {"interests": ["nature"], "avoid": ["meat"]}
    discover_places(trip, Recording())
    # The demo data has no "vegetarian" label, so it falls back to any restaurant.
    assert queries[-2:] == ["vegetarian restaurant", "restaurant"]


def plan_for(pace: str, places: list[dict]) -> dict:
    trip = {
        "trip_id": "t1",
        "destination": "Seattle",
        "start_date": "2026-11-18",
        "end_date": "2026-11-19",
        "mode": "walking",
        "pace": pace,
    }
    itinerary, _ = plan_and_validate(trip, places)
    return itinerary


def sights(count: int) -> list[dict]:
    return [
        place(f"Sight {i}", ["museum"], ["culture"], 47.60 + i * 0.001, -122.33)
        for i in range(count)
    ]


def lunch_spots() -> list[dict]:
    return [
        place("Lunch A", ["restaurant"], ["food"], 47.601, -122.331),
        place("Lunch B", ["restaurant"], ["food"], 47.605, -122.332),
    ]


def test_each_day_gets_one_lunch_stop_around_midday():
    itinerary = plan_for("moderate", sights(10) + lunch_spots())
    for day in itinerary["days"]:
        names = [activity["place"]["name"] for activity in day["activities"]]
        lunches = [n for n in names if n.startswith("Lunch")]
        assert len(lunches) == 1
        assert names.index(lunches[0]) == LUNCH_SLOT
        lunch = day["activities"][LUNCH_SLOT]
        assert "11:" in lunch["start"] or "12:" in lunch["start"] or "13:" in lunch["start"]


def test_pace_sets_how_many_stops_a_day_has():
    relaxed = plan_for("relaxed", sights(12) + lunch_spots())
    packed = plan_for("packed", sights(12) + lunch_spots())
    assert [len(d["activities"]) for d in relaxed["days"]] == [3, 3]
    assert [len(d["activities"]) for d in packed["days"]] == [5, 5]


def test_lunch_skips_a_dinner_only_restaurant():
    # 2026-11-18 is a Wednesday. "Dinner Only" opens at 17:00, like Tulio in the live test.
    dinner_only = place("Dinner Only", ["restaurant"], ["food"], 47.6001, -122.3301)
    dinner_only["hours"] = [{"day": "wednesday", "open": "17:00", "close": "21:00"}]
    open_for_lunch = place("Lunch Place", ["restaurant"], ["food"], 47.603, -122.332)
    open_for_lunch["hours"] = [{"day": "wednesday", "open": "11:00", "close": "15:00"}]
    trip = {
        "trip_id": "t1", "destination": "Seattle", "start_date": "2026-11-18",
        "end_date": "2026-11-18", "mode": "walking", "pace": "moderate",
    }
    itinerary, _ = plan_and_validate(trip, [dinner_only, *sights(5), open_for_lunch])
    names = [a["place"]["name"] for a in itinerary["days"][0]["activities"]]
    assert "Lunch Place" in names
    assert "Dinner Only" not in names


def test_famous_food_spot_is_lunch_before_a_closer_restaurant():
    # Seen live: Joe's Pizza and Ess-a-Bagel were found but lost lunch to closer places.
    nearby = place("Corner Diner", ["restaurant"], ["food"], 47.6001, -122.3301)
    famous = place("Joe's Pizza", ["fast_food"], ["food"], 47.615, -122.34)
    famous["local_signal"] = "tourist"

    itinerary = plan_for("moderate", sights(10) + [nearby, famous])

    lunches = [day["activities"][LUNCH_SLOT]["place"]["name"] for day in itinerary["days"]]
    assert lunches[0] == "Joe's Pizza"  # famous first
    assert "Corner Diner" in lunches  # the nearby one is still used on another day
