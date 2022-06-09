from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Sum, Q
from django.db.models.functions import Now, TruncMonth

from visits.app.util import utcnow, first_day_of_month, last_day_of_month


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
        """Calculates the number of plan minutes remaining for the given
        month/year based on the number of visits scheduled.
        """
        debits = self.account.minuteledger_set.filter(
            cancelled=False,
            amount__lt=0,
            created__gte=first_day_of_month(month, year),
            created__lte=last_day_of_month(month, year),
        ).aggregate(Sum("amount"))

        total = abs(debits["amount__sum"] or 0)

        if self.plan_minutes > total:
            return self.plan_minutes - total

        return 0

    @property
    def current_plan_minutes_remaining(self):
        now = utcnow()
        return self.plan_minutes_remaining(now.month, now.year)

    def minutes_available(self, month, year):
        """Returns the number of minutes available for scheduling new visits
        for the given month/year. This is kind of complicated to calculate,
        because monthly plan minutes are ephemeral and minutes used each month
        only count against banked minutes after first hitting that plan minute
        total.

        The member earns banked minutes by fulfilling visits as a pal. Those
        are simple and can be summed by aggregating all positive entries in
        their ledger.

        To figure out how many minutes a member has used each month, we first
        have to collect the aggregate sum of minutes used each month. Any
        minutes used above the number of monthly plan_minutes represents the
        total debit to count against the member's banked minutes.

        Finally, we add in any remaining minutes from the member's plan for the
        selected month.
        """
        ledger = self.account.minuteledger_set.filter(cancelled=False)

        # Sum up credits
        credits = ledger.filter(amount__gt=0).aggregate(Sum("amount"))["amount__sum"] or 0

        # Select debits
        debits_by_month = ledger.filter(amount__lt=0)
        # Group by YYYY-MM
        debits_by_month = debits_by_month.annotate(month=TruncMonth("created")).values("month")
        # Add up amounts and subtract from plan_minutes (total will be
        # negative, so total + plan_minutes == plan_minutes - -total)
        debits_by_month = debits_by_month.annotate(total=Sum("amount") + self.plan_minutes).values("month", "total")
        # Limit results to those where the total of debits is greater than the
        # monthly plan minutes
        debits_by_month = debits_by_month.filter(total__lt=0)
        # Sum all debits
        debits = sum(row["total"] for row in debits_by_month)

        # Get the number of minutes remaining in the member's plan
        plan_minutes = self.plan_minutes_remaining(month, year)

        return  plan_minutes + credits + debits

    @property
    def current_minutes_available(self):
        now = utcnow()
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
    def is_over(self):
        return utcnow() >= (self.when + timedelta(minutes=self.minutes))

    @property
    def has_started(self):
        return utcnow() > self.when

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

        return self.visit.is_over

    @property
    def is_cancellable(self):
        if self.completed:
            return False

        if self.cancelled:
            return False

        return not self.visit.has_started


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
        cancelled = " (cancelled)" if self.cancelled else ""
        return f"{self.created} | {amount} | {self.account} {cancelled}"
