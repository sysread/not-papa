"""Logic for scheduling, accepting, cancelling, and completing visits for
Members and Pals.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from visits.app.util import utcnow
from visits.models import Visit, Fulfillment, MinuteLedger


MIN_VISIT_LENGTH = 10
DEFAULT_VISIT_LENGTH = 60
FULFILLMENT_PAL_CUT = 0.85


def validate_new_visit(member, when, minutes):
    """Raises a ValidationError if the new visit would occur in the past or if
    the member does not have the accrued minutes to schedule a new visit during
    the specified time period.
    """
    if when <= utcnow():
        raise ValidationError("Visits must be scheduled in advance.")

    available = member.minutes_available(when.month, when.year)

    if minutes > available:
        raise ValidationError(f"You have {available} minutes remaining this month. You can earn more minutes by visiting other members, cancelling planned visits, or scheduling farther into the future.")


@transaction.atomic
def create_visit(member, when, minutes, tasks, commit=True):
    """Creates a new Visit. If commit is True, logs the minutes used by the
    member and commits the changes to the database.
    """
    visit = Visit(member=member, when=when, minutes=minutes, tasks=tasks)

    if commit:
        visit.save()
        minutes = MinuteLedger(account=member.account, visit=visit, reason=MinuteLedger.VISIT_SCHEDULED, amount=-minutes)
        minutes.save()

    return visit


def validate_member_visit_cancellation(member, visit_id):
    """Raises a ValidationError if the Visit does not exist, does not belong to
    the Member, occurred in the past, or has already been cancelled.
    """
    visit = None

    try:
        visit = member.visit_set.get(pk=visit_id)
        if visit.cancelled:
            raise ValidationError("That appointment has already been cancelled.")
        if visit.when <= utcnow():
            raise ValidationError("That appointment has already occurred.")
    except Visit.DoesNotExist:
        raise ValidationError("Appointment not found.")

    return visit


@transaction.atomic
def cancel_visit(visit, commit=True):
    """Cancels a visit. If commit is True, additionally cancels any related
    fulfillments and invalidates MinuteLedger entries.
    """
    visit.cancelled = True
    if commit:
        visit.save()
        visit.fulfillment_set.all().update(cancelled=True)
        visit.minuteledger_set.all().update(cancelled=True)


def validate_new_fulfillment(pal, visit_id):
    """Raises a ValidationError if the Pal cannot fulfill this Visit.
    """
    visit = None

    try:
        visit = Visit.objects.get(pk=visit_id)
        if visit.cancelled:
            raise ValidationError("That appointment has been cancelled.")
        if visit.when <= utcnow():
            raise ValidationError("That appointment has already occurred.")
        if visit.fulfillment_set.filter(cancelled=False).count() > 0:
            raise ValidationError("That appointment has already been scheduled with another Pal.")
    except Visit.DoesNotExist:
        raise ValidationError("Appointment not found.")

    return visit


def create_fulfillment(pal, visit, commit=True):
    """Creates a Fulfillment for the Visit by the Pal. The new Fulfillment is
    considered "scheduled" but not "completed".
    """
    fulfillment = Fulfillment(visit=visit, pal=pal)

    if commit:
        fulfillment.save()

    return fulfillment


def validate_fulfillment_completion(fulfillment_id):
    """Raises a ValidationError if the Fulfillment cannot be completed; for
    example, because it has not finished yet.
    """
    fulfillment = None

    try:
        fulfillment = Fulfillment.objects.get(pk=fulfillment_id)

        if fulfillment.completed:
            raise ValidationError("This fulfillment has already been completed.")

        if fulfillment.cancelled:
            raise ValidationError("This fulfillment was cancelled.")

        if fulfillment.visit.cancelled:
            raise ValidationError("This appointment was cancelled by the member.")

        if not fulfillment.visit.is_over:
            raise ValidationError("This appointment is not yet complete.")

    except Visit.DoesNotExist:
        raise ValidationError("Fulfillment for this Visit not found")

    return fulfillment


@transaction.atomic
def complete_fulfillment(fulfillment, commit=True):
    """Completes a Fulfillment. If commit is True, saves the changes and logs
    the added minutes to the Pal's ledger, at the rate of FULFILLMENT_PAL_CUT.
    """
    fulfillment.completed = True

    if commit:
        fulfillment.save()

        # Charge a 15% fee for minutes earned, but take a short-cut by
        # hard-coding the fee instead of making it config or storing it in
        # the database or something. :D
        MinuteLedger(
            account=fulfillment.pal.account,
            visit=fulfillment.visit,
            reason=MinuteLedger.VISIT_FULFILLED,
            amount=(FULFILLMENT_PAL_CUT * fulfillment.visit.minutes),
        ).save()


def validate_fulfillment_cancellation(fulfillment_id):
    """Raises a ValidationError if the Fulfillment cannot be cancelled; for
    example, because it has not finished yet.
    """
    fulfillment = None

    try:
        fulfillment = Fulfillment.objects.get(pk=fulfillment_id)

        if fulfillment.completed:
            raise ValidationError("That fulfillment has already been completed.")

        if fulfillment.cancelled:
            raise ValidationError("That fulfillment was cancelled.")

        if fulfillment.visit.has_started:
            raise ValidationError("This appointment has already started.")

    except Visit.DoesNotExist:
        raise ValidationError("Fulfillment for this Visit not found")

    return fulfillment


def cancel_fulfillment(fulfillment, commit=True):
    """Cancels the fulfillment, committing the changes to the database if
    commit is True.
    """
    fulfillment.cancelled = True
    if commit:
        fulfillment.save()
