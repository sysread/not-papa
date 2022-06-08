import django.forms as forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

import visits.app.scheduling as scheduling
import visits.app.account as account


class UserRegistrationForm(UserCreationForm):
    """It's a little goofy, but the built-in django user creation form does not
    offer a simple way to make the email field required. So here we are.

    Additionally creates a Pal and Member account for new Users.
    """
    first_name = forms.CharField(label='First name', required=True)
    last_name = forms.CharField(label='Last name', required=True)
    email = forms.EmailField(label="Email address", required=True)
    minutes = forms.IntegerField(label="Monthly minutes", required=False, help_text="If your insurance covers this service, please enter the number of minutes per month you plan allows.")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2")

    def save(self, commit=True):
        return account.add_new_account(
            self.cleaned_data["first_name"],
            self.cleaned_data["last_name"],
            self.cleaned_data["email"],
            self.cleaned_data["password1"],
            self.cleaned_data["minutes"] or 0,
            commit=commit,
        )


class UserForm(forms.Form):
    """A form configured to include the logged in user, with convenience
    properties to access the user's Member and Pal accounts.
    """

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)

    @property
    def member(self):
        return self.user.member

    @property
    def pal(self):
        return self.user.pal


class MemberVisitRequestForm(UserForm):
    when = forms.DateTimeField(required=True, help_text="When would you like one of our Pals to visit you?")
    minutes = forms.IntegerField(required=True, initial=scheduling.DEFAULT_VISIT_LENGTH, min_value=scheduling.MIN_VISIT_LENGTH, help_text="How many minutes would you like to schedule this visit for?")
    tasks = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': 80, 'rows': 6}), help_text="Please provide some basic details about what kinds of things our Pal should be ready to help with.")

    def clean(self):
        """Adds additional validation to ensure that the member has the minutes
        available for the requested visit.
        """
        data = super().clean()
        scheduling.validate_new_visit(self.member, data["when"], data["minutes"])
        return data

    def save(self, commit=True):
        data = self.cleaned_data
        return scheduling.create_visit(self.member, data["when"], data["minutes"], data["tasks"], commit)


class CancelRequestedVisitForm(UserForm):
    """Cancels a visit after validating that it is possible to do so.
    """
    visit_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        """Validates that the visit can indeed be cancelled.
        """
        cleaned_data = super().clean()
        cleaned_data["visit"] = scheduling.validate_member_visit_cancellation(self.member, cleaned_data["visit_id"])
        return cleaned_data

    def save(self, commit=True):
        scheduling.cancel_visit(self.cleaned_data["visit"], commit)


class AcceptVisitForm(UserForm):
    """Assigns a Visit to a Pal by creating a Fulfillment for that visit.
    """
    visit_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["visit"] = scheduling.validate_pal_fulfillment(self.pal, cleaned_data["visit_id"])
        return cleaned_data

    def save(self, commit=True):
        scheduling.create_fulfillment(self.pal, self.cleaned_data["visit"], commit)


class CompleteFulfillmentForm(UserForm):
    """Completes a Fulfillment for a Visit that has been assigned to a Pal.
    """
    fulfillment_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["fulfillment"] = scheduling.validate_fulfillment_completion(cleaned_data["fulfillment_id"])
        return cleaned_data

    def save(self, commit=True):
        scheduling.complete_fulfillment(self.cleaned_data["fulfillment"], commit)


class CancelFulfillmentForm(UserForm):
    """Cancels an incomplete Fulfillment for a Visit that has been assigned to
    a Pal.
    """
    fulfillment_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["fulfillment"] = scheduling.validate_fulfillment_cancellation(cleaned_data["fulfillment_id"])
        return cleaned_data

    def save(self, commit=True):
        scheduling.cancel_fulfillment(self.cleaned_data["fulfillment"])
