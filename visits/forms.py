import datetime

import django.forms as forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Member, Pal, Visit, Fulfillment


class UserRegistrationForm(UserCreationForm):
    """It's a little goofy, but the built-in django user creation form does not
    offer a simple way to make the email field required. So here we are.
    """
    first_name = forms.CharField(label='First name', required=True)
    last_name = forms.CharField(label='Last name', required=True)
    email = forms.EmailField(label="Email address", required=True)

    minutes = forms.IntegerField(
        label="Monthly minutes",
        help_text="If your insurance covers this service, please enter the number of minutes per month you plan allows.",
        required=False,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")

    @transaction.atomic
    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
            Member(account=user, plan_minutes=self.cleaned_data["minutes"]).save()
            Pal(account=user).save()

        return user


class MemberVisitRequestForm(forms.Form):
    when = forms.DateTimeField(
        required=True,
        help_text="When would you like one of our Pals to visit you?",
    )

    minutes = forms.IntegerField(
        required=True,
        initial=60,
        min_value=10,
        help_text="How many minutes would you like to schedule this visit for?",
    )

    tasks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 6}),
        help_text="Please provide some basic details about what kinds of things our Pal should be ready to help with.",
    )

    def __init__(self, user, data=None, *args, **kwargs):
        self.member = user.member
        super(MemberVisitRequestForm, self).__init__(data, *args, **kwargs)

    def clean(self):
        """Adds additional validation to ensure that the member has the minutes
        available for the requested visit.
        """
        cleaned_data = super().clean()

        minutes_available = self.member.minutes_available(
            month=cleaned_data["when"].month,
            year=cleaned_data["when"].year,
        )

        if cleaned_data["minutes"] > minutes_available:
            raise ValidationError(f"You have a maximum of {minutes_available} minutes remaining for visits this month. You can earn more minutes by visiting other members, cancelling planned visits, or scheduling farther into the future.")

        return cleaned_data

    def save(self, commit=True):
        if self.cleaned_data["when"] < datetime.datetime.now(datetime.timezone.utc):
            raise ValidationError("Visits must be scheduled in advance.")

        visit = Visit(
            member=self.member,
            when=self.cleaned_data["when"],
            minutes=self.cleaned_data["minutes"],
            tasks=self.cleaned_data["tasks"],
        )

        if commit:
            visit.save()

        return visit
