# tools/

**Owner:** Tools Eng.

**What goes here:** Small helpers that talk to outside services like Geoapify, Mapbox and Transitous. Agents call these to look up real places and travel times.

**What is here now:**
- `base.py`: the `PlaceSearch` interface every place search must follow.
- `place.py`: the `Place` shape (temporary copy, to be replaced by `app/models` once merged).
- `mock_places.py` + `seattle_seed.py`: a no-keys search over real Seattle places (DEMO_MODE).
- `geoapify.py`: real place search with Geoapify (free plan, OpenStreetMap data). No ratings or prices, so those stay `None`.
- `osm_hours.py`: turns OpenStreetMap hours text (`"Mo-Fr 07:00-18:00"`) into structured opening periods.
- `travel_time.py`: `travel_minutes(origin, destination, mode)`. Mapbox for walking/cycling/driving, Transitous for transit, a rough estimate in DEMO_MODE or when a provider fails.
- `get_place_search()` in `__init__.py`: the one function the rest of the app should call. It returns Geoapify when `DEMO_MODE=false` and `GEOAPIFY_API_KEY` is set, otherwise the mock.

**Attribution (required by the Geoapify free plan):** any screen that shows Geoapify places must show "Powered by Geoapify" and "© OpenStreetMap contributors".
