from django.conf import settings
from django.db import models


class Pal(models.Model):
    """A pal account, associated with a registered user account, is able to
    fulfill visits to members.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f'<pal> {str(self.account)}'


class Member(models.Model):
    """A member account, associated with a registered user account, is able to
    request visits by pals.
    """
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    plan_minutes = models.PositiveIntegerField()

    def __str__(self):
        return f'<member> {str(self.account)}'


class Visit(models.Model):
    """On its own, a visit requested by a member. Once it has been fulfilled by
    a pal, a linked fulfillment is created.
    """
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    when = models.DateTimeField()
    minutes = models.PositiveIntegerField()
    tasks = models.TextField()
    cancelled = models.BooleanField()

    def __str__(self):
        return f'Visit {self.member} for {self.minutes} minutes on {self.when}'

    @property
    def is_fulfilled(self):
        return self.fulfillment is not None


class Fulfillment(models.Model):
    """Records when a visit is fulfilled by a pal.
    """
    visit = models.OneToOneField(Visit, on_delete=models.PROTECT)
    pal = models.ForeignKey(Pal, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.pal} fulfilled {self.visit}'
