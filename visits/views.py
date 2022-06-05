from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .forms import UserRegistrationForm, MemberVisitRequestForm, CancelRequestedVisitForm


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


# TODO: On successful submission, redirect to list of requested, scheduled, and
# fulfilled visits.
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
    visits = [(v, CancelRequestedVisitForm(initial={"visit_id": v.id})) for v in query.all()]

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
        form = CancelRequestedVisitForm(request.POST)
        if form.is_valid():
            form.save()

    return redirect("list-visits")


@login_required
def schedule_fulfillment(request):
    pass


# TODO: add to pal.banked_minutes when fulfilling a visit
@login_required
def complete_fulfillment(request):
    pass
