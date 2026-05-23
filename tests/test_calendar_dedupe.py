import datetime
import unittest

from calendar_dedupe import expand_manual_recurring_events


class CalendarDedupeTests(unittest.TestCase):
    def test_expands_manual_weekly_recurrence_from_explicit_rule(self):
        seed_event = {
            "id": "manual_food_distribution",
            "name": "Columbia Community Care Weekly Food Distribution",
            "startDate": "2026-05-23T09:00:00-04:00",
            "endTime": "2026-05-23T11:00:00-04:00",
            "recurring": True,
            "recurrence": {
                "freq": "weekly",
                "interval": 1,
                "byweekday": ["SA"],
            },
        }

        expanded = expand_manual_recurring_events([seed_event], datetime.date(2026, 5, 23))

        self.assertGreater(len(expanded), 10)
        self.assertEqual(expanded[0]["startDate"], "2026-05-23T09:00:00-04:00")
        self.assertEqual(expanded[1]["startDate"], "2026-05-30T09:00:00-04:00")
        self.assertEqual(expanded[0]["id"], "manual_food_distribution__2026-05-23")
        self.assertEqual(expanded[1]["id"], "manual_food_distribution__2026-05-30")

    def test_respects_exclude_dates_for_manual_recurrence(self):
        seed_event = {
            "id": "manual_service",
            "name": "Volunteer Shift",
            "startDate": "2026-05-23T09:00:00-04:00",
            "endTime": "2026-05-23T11:00:00-04:00",
            "recurring": True,
            "recurrence": {
                "freq": "weekly",
                "interval": 1,
                "byweekday": ["SA"],
                "exclude_dates": ["2026-05-30"],
            },
        }

        expanded = expand_manual_recurring_events([seed_event], datetime.date(2026, 5, 23))
        start_dates = {event["startDate"] for event in expanded}

        self.assertIn("2026-05-23T09:00:00-04:00", start_dates)
        self.assertNotIn("2026-05-30T09:00:00-04:00", start_dates)


if __name__ == "__main__":
    unittest.main()
