from django.test import TestCase
from django.contrib.auth.models import User

import visits.app.account as account
from visits.models import Member, Pal


class AccountTest(TestCase):
    def test__add_new_account(self):
        user = account.add_new_account("Joe", "Blow", "someone@somewhere.com", "super secret", 90)

        self.assertIsInstance(user, User)
        self.assertEqual(user.first_name, "Joe")
        self.assertEqual(user.last_name, "Blow")
        self.assertEqual(user.email, "someone@somewhere.com")

        self.assertIsInstance(user.member, Member)
        self.assertEqual(user.member.plan_minutes, 90)

        self.assertIsInstance(user.pal, Pal)
