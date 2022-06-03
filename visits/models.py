from django.db import models
from django.contrib.auth.models import User


class Plan(models.Model):
    name = models.CharField(max_length=255, unique=True)
    hours = models.PositiveIntegerField()


class Pal(models.Model):
    account = models.ForeignKey(User, on_delete=models.PROTECT)


class Member(models.Model):
    account = models.ForeignKey(User, on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)


class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    when = models.DateTimeField()
    minutes = models.PositiveIntegerField()
    tasks = models.TextField()
    cancelled = models.BooleanField()


class Fulfillment(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT)
    pal = models.ForeignKey(Pal, on_delete=models.PROTECT)
