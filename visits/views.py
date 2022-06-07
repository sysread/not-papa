from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import Visit
from .forms import UserRegistrationForm,\
    MemberVisitRequestForm, \
    CancelRequestedVisitForm, \
    AcceptVisitForm, \
    CompleteFulfillmentForm, \
    CancelFulfillmentForm


def index(request):
    """Displays the homepage.
    """
    return render(request, 'index.html', {})


def register(request):
    """Registers a new user account. For every new user, both a member and pal
    account are created.
    """
    form = UserRegistrationForm()

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")

    return render(request, "registration/register.html", {
        "form": form,
    })


@login_required
def request_visit(request):
    """Displays a form allowing members to request a visit by a pal.
    """
    form = MemberVisitRequestForm(request.user)

    if request.method == "POST":
        form = MemberVisitRequestForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect("list-visits")

    return render(request, "request-visit.html", {
        "form": form,
    })


@login_required
def list_visits(request):
    """Displays the list of visits.
    """
    query = request.user.member.visit_set.order_by("-when").filter(cancelled=False)
    visits = [(v, CancelRequestedVisitForm(request.user, initial={"visit_id": v.id})) for v in query.all()]

    return render(request, "list-visits.html", {
        "visits": visits,
    })


@login_required
def cancel_visit(request):
    """list_views displays a form to cancel visits requested by the member
    which have not yet been fulfilled. This endpoint handles the POST from that
    form.
    """
    if request.method == "POST":
        form = CancelRequestedVisitForm(request.user, request.POST)
        if form.is_valid():
            form.save()

    return redirect("list-visits")


@login_required
def list_fulfillments(request):
    """Displays two lists. The first is of the Pal's active Fulfillments - that
    is, the pending Visits which they have volunteered to fill. The second list
    displays upcoming Visits which are still waiting to be picked up by a Pal.

    The Pal is able to cancel their commitments to future appointments, accept
    new appointments, and complete Visits which they have finished.
    """
    fulfillments = [
        (
            f,
            CompleteFulfillmentForm(request.user, initial={"fulfillment_id": f.id}),
            CancelFulfillmentForm(request.user, initial={"fulfillment_id": f.id})
        )
        for f in request.user.pal.fulfillment_set.order_by("visit__when").filter(completed=False, cancelled=False).all()
    ]

    visits = [
        (v, AcceptVisitForm(request.user, initial={"visit_id": v.id}))
        for v in Visit.objects.unscheduled().exclude(member=request.user.member).order_by("when").all()
    ]

    return render(request, "list-fulfillments.html", {
        "fulfillments": fulfillments,
        "visits": visits,
    })


@login_required
def schedule_fulfillment(request):
    """list_fulfillments displays a form for the Pal to accept available,
    unscheduled visits. This endpoint handles the POST from that form.
    """
    if request.method == "POST":
        form = AcceptVisitForm(request.user, request.POST)
        if form.is_valid():
            form.save()

    return redirect("list-fulfillments")


@login_required
def complete_fulfillment(request):
    """list_fulfillments displays a form for the Pal to complete previously
    accepted/scheduled visits. This endpoint handles the POST from that form.
    """
    if request.method == "POST":
        form = CompleteFulfillmentForm(request.user, request.POST)
        if form.is_valid():
            form.save()

    return redirect("list-fulfillments")


@login_required
def cancel_fulfillment(request):
    """list_fulfillments displays a form for the Pal to cancel previously
    accepted/scheduled visits. This endpoint handles the POST from that form.
    """
    if request.method == "POST":
        form = CancelFulfillmentForm(request.user, request.POST)
        if form.is_valid():
            form.save()

    return redirect("list-fulfillments")
