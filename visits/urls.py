from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register', views.register, name='register'),
    path('request-visit', views.request_visit, name='request-visit'),
    path('list-visits', views.list_visits, name='list-visits'),
]
