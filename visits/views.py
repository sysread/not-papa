from django.shortcuts import render, redirect

from .forms import UserRegistrationForm


def index(request):
    return render(request, 'index.html', {})


def register(request):
    form = UserRegistrationForm()

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(index)

    return render(request, 'registration/register.html', {
        'form': form
    })


def request_visit(request):
    pass
