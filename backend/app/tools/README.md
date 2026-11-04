# tools/

**Owner:** Tools Eng.

**What goes here:** Small helpers that talk to outside services like Mapbox and Foursquare. Agents call these to look up real places and travel times.

**What is here now (T-01):**
- `base.py`: the `PlaceSearch` interface every place search must follow.
- `place.py`: the `Place` shape (temporary copy, to be replaced by `app/models` once merged).
- `mock_places.py` + `seattle_seed.py`: a no-keys search over real Seattle places (DEMO_MODE).
- `get_place_search()` in `__init__.py`: the one function the rest of the app should call.

**Not built yet:** the real Foursquare and Mapbox adapters (Discovery story, US-04).
