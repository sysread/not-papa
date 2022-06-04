from django.db import models
from django.contrib.auth.models import User


class Pal(models.Model):
    account = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f'Pal: {str(self.account)}'


class Member(models.Model):
    account = models.ForeignKey(User, on_delete=models.PROTECT)
    plan_minutes = models.PositiveIntegerField()

    def __str__(self):
        return f'Member: {str(self.account)}'


class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    when = models.DateTimeField()
    minutes = models.PositiveIntegerField()
    tasks = models.TextField()
    cancelled = models.BooleanField()

    def __str__(self):
        return f'Visit: {self.member} for {self.minutes} on {self.when}'


class Fulfillment(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT)
    pal = models.ForeignKey(Pal, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.pal} fulfilled {self.visit}'
