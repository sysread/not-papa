import django.forms as forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from .models import Member, Pal


class UserRegistrationForm(UserCreationForm):
    """It's a little goofy, but the built-in django user creation form does not
    offer a simple way to make the email field required. So here we are.
    """
    email = forms.EmailField(
        label=_("Email address"),
        help_text=_("Please enter your email address."),
        required=True,
    )

    minutes = forms.IntegerField(
        label=_("Monthly minutes"),
        help_text=_("If your insurance covers this service, please enter the number of minutes allowed per month."),
        required=False,
    )

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    @transaction.atomic
    def save(self, commit=True):
        self.cleaned_data["username"] = self.cleaned_data["email"]
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]

        if commit:
            user.save()
            Member(account=user, plan_minutes=self.cleaned_data["minutes"]).save()
            Pal(account=user).save()

        return user
