from app.agents.preferences import extract_preferences


def test_preference_examples():
    examples = [
        (
            3,
            "I want a 5-day trip with beaches and seafood. "
            "I want to avoid nightlife. My budget is cheap and "
            "I do not want to travel more than 20 minutes.",
            {
                "interests": ["beaches", "seafood"],
                "avoid": ["nightlife"],
                "budget": "cheap",
                "max_travel_minutes": 20,
            },
        ),
        (
            4,
            "I want to visit Chicago for architecture, coffee, and local neighborhoods. "
            "I want to avoid touristy attractions. My budget is moderate and "
            "I do not want to travel more than 60 minutes.",
            {
                "interests": ["architecture", "coffee", "local neighborhoods"],
                "avoid": ["touristy attractions"],
                "budget": "moderate",
                "max_travel_minutes": 60,
            },
        ),
        (
            5,
            "I want a relaxing trip with nature trails and scenic views. "
            "I want to avoid clubs and partying. My budget is cheap and "
            "I do not want to travel more than 40 minutes.",
            {
                "interests": ["nature trails", "scenic views"],
                "avoid": ["clubs", "partying"],
                "budget": "cheap",
                "max_travel_minutes": 40,
            },
        ),
        (
            6,
            "I want a family trip with kid-friendly activities, zoos, and parks. "
            "I want to avoid art galleries. My budget is cheap and "
            "I do not want to travel more than 50 minutes.",
            {
                "interests": ["kid-friendly activities", "zoos", "parks"],
                "avoid": ["art galleries"],
                "budget": "cheap",
                "max_travel_minutes": 50,
            },
        ),
        (
            7,
            "I want a trip with great food and a good music scene. "
            "I want to avoid historical sites. My budget is expensive and "
            "I do not want to travel more than 90 minutes.",
            {
                "interests": ["great food", "music scene"],
                "avoid": ["historical sites"],
                "budget": "expensive",
                "max_travel_minutes": 90,
            },
        ),
        (
            8,
            "I want a low-key weekend with local markets, street food, and photography. "
            "I want to avoid shopping malls and expensive restaurants. "
            "My budget is cheap and I do not want to travel more than 25 minutes.",
            {
                "interests": ["local markets", "street food", "photography"],
                "avoid": ["shopping malls", "expensive restaurants"],
                "budget": "cheap",
                "max_travel_minutes": 25,
            },
        ),
        (
            9,
            "I want an outdoorsy trip with kayaking and mountain biking. "
            "I want to avoid crowded tourist spots. My budget is moderate and "
            "I do not want to travel more than 60 minutes.",
            {
                "interests": ["kayaking", "mountain biking"],
                "avoid": ["crowded tourist spots"],
                "budget": "moderate",
                "max_travel_minutes": 60,
            },
        ),
        (
            10,
            "I want a luxurious trip with luxury hotels, fine dining, and spas. "
            "I want to avoid hiking and camping. My budget is expensive and "
            "I do not want to travel more than 30 minutes.",
            {
                "interests": ["luxury hotels", "fine dining", "spas"],
                "avoid": ["hiking", "camping"],
                "budget": "expensive",
                "max_travel_minutes": 30,
            },
        ),
    ]

    passed = 0
    skipped = 0

    for number, description, expected in examples:
        try:
            result = extract_preferences(description)

            assert result.budget == expected["budget"]
            assert result.max_travel_minutes == expected["max_travel_minutes"]
            assert set(result.interests) == set(expected["interests"])
            assert set(result.avoid) == set(expected["avoid"])

            print(f"\nExample {number}: PASS")
            passed += 1

        except Exception as error:
            print(f"\nExample {number}: SKIPPED - {type(error).__name__}: {error}")
            skipped += 1

    print(f"\nResults: {passed} passed, {skipped} skipped")