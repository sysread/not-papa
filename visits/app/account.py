"""Logic for managing user accounts, for both Pals and Members.
"""
from django.db import transaction
from django.contrib.auth.models import User

from visits.models import Pal, Member


@transaction.atomic
def add_new_account(first, last, email, pwd, member_plan_minutes, commit=True):
    """Creates a new user account. If commit is True, saves the new account and
    creates a corresponding Member and Pal account.
    """
    user = User(first_name=first, last_name=last, email=email, username=email)
    user.set_password(pwd)

    if commit:
        user.save()

        member = Member(account=user, plan_minutes=member_plan_minutes)
        member.save()

        pal = Pal(account=user)
        pal.save()

    return user
