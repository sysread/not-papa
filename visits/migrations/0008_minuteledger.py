# Generated by Django 3.2.7 on 2022-06-07 19:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('visits', '0007_remove_pal_banked_minutes'),
    ]

    operations = [
        migrations.CreateModel(
            name='MinuteLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('amount', models.IntegerField()),
                ('reason', models.CharField(choices=[('visit_scheduled', 'Member scheduled a visit'), ('visit_fulfilled', 'Pal completed a visit'), ('cancellation', 'Cancels an earlier transaction')], max_length=100)),
                ('cancelled', models.BooleanField(default=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('visit', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='visits.visit')),
            ],
        ),
    ]