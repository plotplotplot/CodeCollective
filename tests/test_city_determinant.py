import unittest

from city_determinant import determine_event_city


class CityDeterminantTests(unittest.TestCase):
    def test_classifies_philadelphia_from_location(self):
        event = {
            "name": "Founders Meetup",
            "location": {
                "city": "Philadelphia",
                "state": "PA",
                "address": "123 Market St, Philadelphia, PA",
            },
        }
        result = determine_event_city(event)
        self.assertEqual(result.get("city"), "philadelphia")
        self.assertIn(result.get("confidence"), {"high", "medium"})

    def test_classifies_dc_from_state(self):
        event = {
            "name": "Policy Forum",
            "location": {
                "city": "Washington",
                "state": "DC",
            },
        }
        result = determine_event_city(event)
        self.assertEqual(result.get("city"), "dc")

    def test_classifies_virtual_from_online_signal(self):
        event = {
            "name": "Remote Security Webinar",
            "description": "Join online via Zoom.",
            "location": {"name": "Online Event"},
        }
        result = determine_event_city(event)
        self.assertEqual(result.get("city"), "virtual")


if __name__ == "__main__":
    unittest.main()
