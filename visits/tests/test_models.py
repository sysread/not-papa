from datetime import timedelta

from django.test import TestCase

import visits.app.scheduling as scheduling
from visits.app.util import utcnow
from visits.models import Member, MinuteLedger
from visits.tests import new_user


class MemberTest(TestCase):
    def test__minutes_available(self):
        member = new_user(mins=300)
        pal = new_user(mins=300)
        when = utcnow() - timedelta(hours=1)

        visit = scheduling.create_visit(member.member, when, 100, "do things")
        fulfillment = scheduling.create_fulfillment(pal.pal, visit)

        visit.refresh_from_db()
        fulfillment.refresh_from_db()

        # Before the fulfillment is completed, the visit should count against the
        # member's minutes
        self.assertEqual(member.member.minutes_available(when.month, when.year), 200)

        # But the pal's minutes are unchanged until the fulfillment's actually completed
        self.assertEqual(pal.member.minutes_available(when.month, when.year), 300)

        # Now, fulfill the visit
        scheduling.complete_fulfillment(fulfillment)

        # Member has now used 100 of their 300 minutes (unchanged from before)
        self.assertEqual(member.member.minutes_available(when.month, when.year), 200)

        # Pal has earned 85% of those 100 minutes to add onto their own
        self.assertEqual(pal.member.minutes_available(when.month, when.year), 300 + (100 * scheduling.FULFILLMENT_PAL_CUT))

    def test__plan_minutes_remaining(self):
        member = new_user(mins=300)
        pal = new_user(mins=300)
        when = utcnow() - timedelta(hours=1)

        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 300)

        # Schedule a visit. The minutes are deducted from the member's monthly balance.
        visit1 = scheduling.create_visit(member.member, when, 100, "do things")
        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 200)

        # Schedule pal to fulfill the visit. The member's monthly balance is unchanged.
        fulfillment = scheduling.create_fulfillment(pal.pal, visit1)
        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 200)

        # Complete the visit. The member's monthly balance is unchanged.
        scheduling.complete_fulfillment(fulfillment)
        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 200)

        # Schedule a second visit. The minutes are deducted from the member's balance.
        visit2 = scheduling.create_visit(member.member, when, 50, "do other things")
        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 150)

        # Cancel the visit. The minutes are returned to the member's balance.
        scheduling.cancel_visit(visit2)
        self.assertEqual(member.member.plan_minutes_remaining(when.month, when.year), 200)
