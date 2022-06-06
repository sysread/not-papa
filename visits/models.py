from datetime import datetime, timedelta, timezone


from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now


class Pal(models.Model):
    """A pal account, associated with a registered user account, is able to
    fulfill visits to members.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f'(pal) {self.account.first_name} {self.account.last_name} <{self.account.email}>'

    def banked_minutes(self, month, year):
        fulfillments = self.fulfillment_set.filter(
            visit__when__month=month,
            visit__when__year=year,
            completed=True,
        )

        return fulfillments.aggregate(banked=models.Sum("minutes")).get("banked") or 0

    @property
    def current_banked_minutes(self):
        now = datetime.now(timezone.utc)
        return self.banked_minutes(now.month, now.year)


class Member(models.Model):
    """A member account, associated with a registered user account, is able to
    request visits by pals.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan_minutes = models.PositiveIntegerField()

    def __str__(self):
        return f'(member) {self.account.first_name} {self.account.last_name} <{self.account.email}>'

    def plan_minutes_remaining(self, month, year):
        visits = self.visit_set.filter(
            when__month=month,
            when__year=year,
            cancelled=False,
            fulfillment__completed=True,
        )

        # Count the number of minutes total for those visits
        used = visits.aggregate(minutes_used=models.Sum("minutes")).get("minutes_used") or 0

        return self.plan_minutes - used

    def minutes_available(self, month, year):
        """Calculates the number of minutes available based on the member's
        monthly allowance, minutes used or scheduled for visits in the
        requested month/year, as well as any visits they have fulfilled
        themselves as a pal.
        """
        return self.plan_minutes_remaining(month, year) + self.account.pal.current_banked_minutes

    @property
    def current_minutes_available(self):
        now = datetime.now(timezone.utc)
        return self.minutes_available(now.month, now.year)

    @property
    def current_plan_minutes_remaining(self):
        now = datetime.now(timezone.utc)
        return self.plan_minutes_remaining(now.month, now.year)


class VisitManager(models.Manager):
    def pending(self):
        """Selects all future visits that have not been cancelled.
        """
        return self.filter(cancelled=False, when__gte=Now())

    def unscheduled(self):
        """Selects pending visits which have no active, pending fulfillments.
        """
        return self.pending().filter(Q(fulfillment__isnull=True) | Q(fulfillment__cancelled=True))


class Visit(models.Model):
    """On its own, a visit requested by a member. Once it has been fulfilled by
    a pal, a linked fulfillment is created.
    """
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    when = models.DateTimeField()
    minutes = models.PositiveIntegerField()
    tasks = models.TextField()
    cancelled = models.BooleanField(default=False)

    # Custom model manager
    objects = VisitManager()

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


class Fulfillment(models.Model):
    """Records when a visit is fulfilled by a pal.
    """
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT)
    pal = models.ForeignKey(Pal, on_delete=models.PROTECT)
    completed = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)

    def __str__(self):
        if self.cancelled:
            return f'(Cancelled) {self.visit}'

        if not self.completed:
            return f'(Unfulfilled) {self.visit}'

        return f'{self.pal} fulfilled {self.visit}'

    @property
    def is_ready_to_complete(self):
        if self.completed:
            return False

        if self.cancelled:
            return False

        return datetime.now(timezone.utc) >= (self.visit.when + timedelta(minutes=self.visit.minutes))

    @property
    def is_cancellable(self):
        if self.completed:
            return False

        if self.cancelled:
            return False

        return datetime.now(timezone.utc) < self.visit.when
