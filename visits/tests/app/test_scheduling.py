from datetime import timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError

import visits.app.scheduling as scheduling
from visits.app.util import utcnow
from visits.models import Fulfillment, MinuteLedger
from visits.tests import new_user


class NewVisitTest(TestCase):
    def test__validate_new_visit(self):
        user = new_user()

        scheduling.validate_new_visit(user.member, utcnow() + timedelta(days=1), 30)  # does not raise ValidationError

        # schedule in the past
        with self.assertRaises(ValidationError):
            scheduling.validate_new_visit(user.member, utcnow() - timedelta(days=1), 30)

        # not enough minutes
        with self.assertRaises(ValidationError):
            scheduling.validate_new_visit(user.member, utcnow() + timedelta(days=1), 100)

    def test__create_visit(self):
        user = new_user()

        visit = scheduling.create_visit(user.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
        self.assertEqual(visit.member, user.member)
        self.assertEqual(visit.minutes, 30)

        tx = visit.minuteledger_set.first()
        self.assertEqual(tx.account, user)
        self.assertEqual(tx.visit, visit)
        self.assertEqual(tx.reason, MinuteLedger.VISIT_SCHEDULED)
        self.assertEqual(tx.amount, -30)
        self.assertFalse(tx.cancelled)


class CancelVisitTest(TestCase):
    def test__validate_member_visit_cancellation(self):
        user = new_user()

        visit = scheduling.create_visit(user.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
        scheduling.validate_member_visit_cancellation(user.member, visit.pk)  # does not raise ValidationError

        # cancelled
        visit = scheduling.create_visit(user.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
        visit.cancelled = True
        visit.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_member_visit_cancellation(user.member, visit.pk)

        # can't cancel appointments in the past
        visit = scheduling.create_visit(user.member, utcnow() - timedelta(days=1), 30, "sorting assorted sorts")
        with self.assertRaises(ValidationError):
            scheduling.validate_member_visit_cancellation(user.member, visit.pk)

        # not found
        with self.assertRaises(ValidationError):
            scheduling.validate_member_visit_cancellation(user.member, 9999)

    def test__cancel_visit(self):
        member = new_user()
        pal = new_user()

        visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
        tx = visit.minuteledger_set.first()
        fulfillment = Fulfillment(pal=pal.pal, visit=visit)
        fulfillment.save()

        scheduling.cancel_visit(visit)
        fulfillment.refresh_from_db()
        tx.refresh_from_db()

        self.assertTrue(visit.cancelled)
        self.assertTrue(fulfillment.cancelled)
        self.assertTrue(tx.cancelled)


class NewFulfillmentTest(TestCase):
    def test__validate_new_fulfillment(self):
        member = new_user()
        pal = new_user()
        visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
        scheduling.validate_new_fulfillment(pal.pal, visit.pk)  # does not raise ValidationError

        # visit is cancelled
        with self.assertRaises(ValidationError):
            visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
            scheduling.cancel_visit(visit)
            scheduling.validate_new_fulfillment(pal.pal, visit.pk)

        # visit is in the past
        with self.assertRaises(ValidationError):
            visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
            visit.when = utcnow() - timedelta(days=1)
            visit.save()
            scheduling.validate_new_fulfillment(pal.pal, visit.pk)

        # visit is already scheduled with another pal
        with self.assertRaises(ValidationError):
            visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")
            fulfillment = Fulfillment(pal=pal.pal, visit=visit)
            fulfillment.save()
            scheduling.validate_new_fulfillment(pal.pal, visit.pk)

    def test__create_fulfillment(self):
        member = new_user()
        pal = new_user()
        visit = scheduling.create_visit(member.member, utcnow() + timedelta(days=1), 30, "sorting assorted sorts")

        fulfillment = scheduling.create_fulfillment(pal.pal, visit)
        self.assertEqual(fulfillment.pal, pal.pal)
        self.assertEqual(fulfillment.visit, visit)
        self.assertFalse(fulfillment.completed)
        self.assertFalse(fulfillment.cancelled)


class CompleteFulfillmentTest(TestCase):
    def test__validate_fulfillment_completion(self):
        member = new_user()
        pal = new_user()
        visit = scheduling.create_visit(member.member, utcnow() - timedelta(hours=1), 30, "sorting assorted sorts")
        fulfillment = scheduling.create_fulfillment(pal.pal, visit)

        scheduling.validate_fulfillment_completion(fulfillment.pk)  # does not raise ValidationError

        # fulfillment already completed
        fulfillment.completed = True
        fulfillment.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_completion(fulfillment.pk)

        # fulfillment was cancelled
        fulfillment.completed = False
        fulfillment.cancelled = True
        fulfillment.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_completion(fulfillment.pk)

        # visit was cancelled
        fulfillment.completed = False
        fulfillment.cancelled = False
        fulfillment.save()
        visit.cancelled = True
        visit.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_completion(fulfillment.pk)

        # visit is not yet over
        visit.cancelled = False
        visit.when = utcnow()
        visit.minutes = 30
        visit.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_completion(fulfillment.pk)

    def test__complete_fulfillment(self):
        member = new_user()
        pal = new_user()

        visit = scheduling.create_visit(member.member, utcnow() - timedelta(hours=3), 100, "sorting assorted sorts")
        fulfillment = scheduling.create_fulfillment(pal.pal, visit)
        scheduling.complete_fulfillment(fulfillment)

        fulfillment.refresh_from_db()
        self.assertTrue(fulfillment.completed)

        tx = MinuteLedger.objects.get(visit=visit, account=pal)
        self.assertEqual(tx.reason, MinuteLedger.VISIT_FULFILLED)
        self.assertEqual(tx.amount, 85)  # see visits.app.scheduling.FULFILLMENT_PAL_CUT
        self.assertFalse(tx.cancelled)


class CancelFulfillmentTest(TestCase):
    def test__validate_fulfillment_cancellation(self):
        member = new_user()
        pal = new_user()

        visit = scheduling.create_visit(member.member, utcnow() + timedelta(hours=1), 30, "sorting assorted sorts")
        fulfillment = scheduling.create_fulfillment(pal.pal, visit)

        scheduling.validate_fulfillment_cancellation(fulfillment.pk)  # does not raise ValidationError

        # fulfillment already completed
        fulfillment.completed = True
        fulfillment.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_cancellation(fulfillment.pk)

        # fulfillment cancelled
        fulfillment.completed = False
        fulfillment.cancelled = True
        fulfillment.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_cancellation(fulfillment.pk)

        # visit already started
        fulfillment.completed = False
        fulfillment.cancelled = False
        fulfillment.save()
        visit.when = utcnow() - timedelta(minutes=10)
        visit.save()
        with self.assertRaises(ValidationError):
            scheduling.validate_fulfillment_cancellation(fulfillment.pk)

    def test__cancel_fulfillment(self):
        member = new_user()
        pal = new_user()

        visit = scheduling.create_visit(member.member, utcnow() + timedelta(hours=1), 30, "sorting assorted sorts")
        fulfillment = scheduling.create_fulfillment(pal.pal, visit)

        scheduling.cancel_fulfillment(fulfillment)
        fulfillment.refresh_from_db()

        self.assertTrue(fulfillment.cancelled)
