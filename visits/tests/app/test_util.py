from datetime import datetime, timezone, timedelta

from django.test import TestCase

import visits.app.util as util


class DateTimeUtilTests(TestCase):
    def test__utcnow(self):
        utcnow = util.utcnow()
        now = datetime.now(timezone.utc)
        self.assertLess(utcnow, now + timedelta(minutes=10))
        self.assertGreater(utcnow, now - timedelta(minutes=10))

    def test__first_day_of_month(self):
        dt = util.first_day_of_month(6, 2022)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.year, 2022)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test__last_day_of_month(self):
        dt = util.last_day_of_month(6, 2022)
        self.assertEqual(dt.day, 30)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.year, 2022)
        self.assertEqual(dt.tzinfo, timezone.utc)
