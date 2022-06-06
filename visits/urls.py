from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("register", views.register, name="register"),

    # Member views
    path("request-visit", views.request_visit, name="request-visit"),
    path("list-visits", views.list_visits, name="list-visits"),
    path("cancel-visit", views.cancel_visit, name="cancel-visit"),

    # Pal views
    path("list-fulfillments", views.list_fulfillments, name="list-fulfillments"),
    path("schedule-fulfillment", views.schedule_fulfillment, name="schedule-fulfillment"),
    path("complete-fulfillment", views.complete_fulfillment, name="complete-fulfillment"),
    path("cancel-fulfillment", views.cancel_fulfillment, name="cancel-fulfillment"),
]
