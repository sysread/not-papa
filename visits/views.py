from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .forms import UserRegistrationForm, MemberVisitRequestForm


def index(request):
    return render(request, 'index.html', {})


def register(request):
    form = UserRegistrationForm()

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')

    return render(request, 'registration/register.html', {
        'form': form,
    })


# TODO: On successful submission, redirect to list of requested, scheduled, and
# fulfilled visits.
@login_required
def request_visit(request):
    form = MemberVisitRequestForm(request.user)

    if request.method == 'POST':
        form = MemberVisitRequestForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')

    return render(request, 'request-visit.html', {
        'form': form,
    })


# TODO: add to pal.banked_minutes when fulfilling a visit
