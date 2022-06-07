from calendar import monthrange
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import models
from django.db.models import Sum, Q
from django.db.models.functions import Now, TruncMonth


def last_day_of_month(month, year):
    return datetime(year, month, monthrange(year, month)[1], tzinfo=timezone.utc)


def first_day_of_month(month, year):
    return datetime(year, month, monthrange(year, month)[0], tzinfo=timezone.utc)


class Pal(models.Model):
    """A pal account, associated with a registered user account, is able to
    fulfill visits to members.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

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

    def plan_minutes_remaining(self, month, year):
        debits = self.account.minuteledger_set \
            .filter(cancelled=False, amount__lt=0, created__lte=last_day_of_month(month, year)) \
            .aggregate(Sum("amount"))

        total = abs(debits["amount__sum"] or 0)

        if self.plan_minutes > total:
            return self.plan_minutes - total

        return 0

    @property
    def current_plan_minutes_remaining(self):
        now = datetime.now(timezone.utc)
        return self.plan_minutes_remaining(now.month, now.year)

    def minutes_available(self, month, year):
        ledger = self.account.minuteledger_set.filter(cancelled=False, created__lte=last_day_of_month(month, year))

        debits_by_month = ledger \
            .filter(amount__lt=0) \
            .annotate(month=TruncMonth("created")) \
            .values("month") \
            .annotate(total=Sum("amount") + self.plan_minutes) \
            .values("total") \
            .filter(total__lt=0)

        credits = ledger.filter(amount__gt=0) \
            .annotate(total=Sum("amount")) \
            .values("total")

        return sum(row["total"] for row in credits) + sum(row["total"] for row in debits_by_month)

    @property
    def current_minutes_available(self):
        now = datetime.now(timezone.utc)
        return self.minutes_available(now.month, now.year)


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


class MinuteLedger(models.Model):
    VISIT_SCHEDULED = "visit_scheduled"
    VISIT_FULFILLED = "visit_fulfilled"
    REASONS = [
        (VISIT_SCHEDULED, "Member scheduled a visit"),
        (VISIT_FULFILLED, "Pal completed a visit"),
    ]

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    amount = models.IntegerField()
    reason = models.CharField(max_length=100, choices=REASONS)
    cancelled = models.BooleanField(default=False)

    def __str__(self):
        amount = self.amount if self.amount > 0 else f"({abs(self.amount)})"
        return f"{self.created} | {amount} | {self.account}"
