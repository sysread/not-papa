import datetime

from django.conf import settings
from django.db import models


class Pal(models.Model):
    """A pal account, associated with a registered user account, is able to
    fulfill visits to members.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    banked_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'(pal) {self.account.first_name} {self.account.last_name} <{self.account.email}>'


class Member(models.Model):
    """A member account, associated with a registered user account, is able to
    request visits by pals.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan_minutes = models.PositiveIntegerField()

    def __str__(self):
        return f'(member) {self.account.first_name} {self.account.last_name} <{self.account.email}>'

    def minutes_available(self, month, year):
        """Calculates the number of minutes available based on the member's
        monthly allowance, minutes used or scheduled for visits in the
        requested month/year, as well as any visits they have fulfilled
        themselves as a pal.
        """
        # Get the list of visits scheduled for the requested month/year
        visits = self.visit_set.filter(
            cancelled=False,
            when__month=month,
            when__year=year,
        )

        # Count the number of minutes total for those visits
        used = visits.aggregate(minutes_used=models.Sum("minutes")).get("minutes_used") or 0

        # Return the number of minutes available for scheduling new visits
        # during month/year.
        return self.plan_minutes + self.account.pal.banked_minutes - used


class Visit(models.Model):
    """On its own, a visit requested by a member. Once it has been fulfilled by
    a pal, a linked fulfillment is created.
    """
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    when = models.DateTimeField()
    minutes = models.PositiveIntegerField()
    tasks = models.TextField()
    cancelled = models.BooleanField(default=False)

    def __str__(self):
        return f'Visit ({self.str_state}) {self.member} for {self.minutes} minutes on {self.when}'

    @property
    def fulfillment(self):
        # NOTE: django caches result sets
        return self.fulfillment_set.filter(cancelled=False).first()

    @property
    def is_scheduled(self):
        return self.fulfillment is not None and self.fulfillment.completed is False

    @property
    def is_completed(self):
        return self.fulfillment is not None and self.fulfillment.completed is True

    @property
    def str_state(self):
        if self.cancelled:
            return "cancelled"
        elif self.is_completed:
            return "completed"
        elif self.is_scheduled:
            return "scheduled"
        else:
            return "unscheduled"

    def is_cancellable(self):
        """Returns a tuple of (can_cancel(bool), reason(string)).
        """
        # You can't cancel and already fulfilled visit
        if self.is_completed:
            return (False, "This visit was already completed.")

        # If the visit has been scheduled with a member, then don't allow
        # cancellation after the appointment has started.
        #
        # TODO: there should be some grace period for the pal so they don't
        # have an appointment they've already left for cancelled out from under
        # them.
        if self.is_scheduled and self.when <= datetime.datetime.now():
            return (False, "Unable to cancel a visit which has already begun.")

        return (True, None)


class Fulfillment(models.Model):
    """Records when a visit is fulfilled by a pal.
    """
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT)
    pal = models.ForeignKey(Pal, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)

    def __str__(self):
        if self.pal is None:
            return f'(Unfulfilled) {self.visit}'

        return f'{self.pal} fulfilled {self.visit}'
