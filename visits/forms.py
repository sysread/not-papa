from datetime import datetime, timezone

import django.forms as forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Member, Pal, Visit, Fulfillment, MinuteLedger


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

            member = Member(account=user, plan_minutes=self.cleaned_data["minutes"])
            member.save()

            pal = Pal(account=user)
            pal.save()

        return user


class MemberForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        self.member = user.member
        super(MemberForm, self).__init__(*args, **kwargs)


class PalForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        self.pal = user.pal
        super(PalForm, self).__init__(*args, **kwargs)


class MemberVisitRequestForm(MemberForm):
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

    def clean(self):
        """Adds additional validation to ensure that the member has the minutes
        available for the requested visit.
        """
        cleaned_data = super().clean()
        month = cleaned_data["when"].month
        year = cleaned_data["when"].year

        plan = self.member.plan_minutes_remaining(month, year)
        banked = self.member.minutes_available(month, year)
        available = plan + banked

        if cleaned_data["minutes"] > available:
            raise ValidationError(f"You have a maximum of {available} minutes remaining for visits this month. You can earn more minutes by visiting other members, cancelling planned visits, or scheduling farther into the future.")

        return cleaned_data

    def save(self, commit=True):
        if self.cleaned_data["when"] < datetime.now(timezone.utc):
            raise ValidationError("Visits must be scheduled in advance.")

        visit = Visit(
            member=self.member,
            when=self.cleaned_data["when"],
            minutes=self.cleaned_data["minutes"],
            tasks=self.cleaned_data["tasks"],
        )

        if commit:
            visit.save()

            MinuteLedger(
                account=self.member.account,
                visit=visit,
                reason=MinuteLedger.VISIT_SCHEDULED,
                amount=-self.cleaned_data["minutes"],
            ).save()

        return visit


class CancelRequestedVisitForm(MemberForm):
    """Cancels a visit after validating that it is possible to do so.
    """
    visit_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        """Validates that the visit can indeed be cancelled.
        """
        cleaned_data = super().clean()

        try:
            cleaned_data["visit"] = self.member.visit_set.pending().get(pk=cleaned_data["visit_id"])
        except Visit.DoesNotExist:
            raise ValidationError("Visit not found")

        return cleaned_data

    def save(self, commit=True):
        self.cleaned_data["visit"].cancelled = True
        if commit:
            self.cleaned_data["visit"].save()
            self.cleaned_data["visit"].fulfillment_set.all().update(cancelled=True)
            self.cleaned_data["visit"].minuteledger_set.all().update(cancelled=True)


class AcceptVisitForm(PalForm):
    """Assigns a Visit to a Pal by creating a Fulfillment for that visit.
    """
    visit_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()

        try:
            cleaned_data["visit"] = Visit.objects.unscheduled().get(pk=cleaned_data["visit_id"])
        except Visit.DoesNotExist:
            raise ValidationError("Visit not found")

        return cleaned_data

    def save(self, commit=True):
        fulfillment = Fulfillment(visit=self.cleaned_data["visit"], pal=self.pal)
        if commit:
            fulfillment.save()


class CompleteFulfillmentForm(PalForm):
    """Completes a Fulfillment for a Visit that has been assigned to a Pal.
    """
    fulfillment_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()

        try:
            fulfillment = Fulfillment.objects.get(pk=cleaned_data["fulfillment_id"])
            if not fulfillment.is_ready_to_complete:
                raise ValidationError('This visit is not finished yet.')
            cleaned_data["fulfillment"] = fulfillment
        except Visit.DoesNotExist:
            raise ValidationError("Fulfillment for this Visit not found")

        return cleaned_data

    def save(self, commit=True):
        self.cleaned_data["fulfillment"].completed = True

        if commit:
            self.cleaned_data["fulfillment"].save()
            self.pal.save()

            # Charge a 15% fee for minutes earned, but take a short-cut by
            # hard-coding the fee instead of making it config or storing it in
            # the database or something. :D
            MinuteLedger(
                account=self.pal.account,
                visit=self.cleaned_data["fulfillment"].visit,
                reason=MinuteLedger.VISIT_FULFILLED,
                amount=(0.85 * self.cleaned_data["fulfillment"].visit.minutes),
            ).save()


class CancelFulfillmentForm(PalForm):
    """Cancels an incomplete Fulfillment for a Visit that has been assigned to a Pal.
    """
    fulfillment_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()

        try:
            fulfillment = Fulfillment.objects.get(pk=cleaned_data["fulfillment_id"])
            if not fulfillment.is_cancellable:
                raise ValidationError('It is too late to cancel this appointment.')
            cleaned_data["fulfillment"] = fulfillment
        except Visit.DoesNotExist:
            raise ValidationError("Fulfillment for this Visit not found")

        return cleaned_data

    def save(self, commit=True):
        self.cleaned_data["fulfillment"].cancelled = True

        if commit:
            self.cleaned_data["fulfillment"].save()
