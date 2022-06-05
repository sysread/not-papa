# Generated by Django 3.2.7 on 2022-06-05 18:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_minutes', models.PositiveIntegerField()),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when', models.DateTimeField()),
                ('minutes', models.PositiveIntegerField()),
                ('tasks', models.TextField()),
                ('cancelled', models.BooleanField()),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='visits.member')),
            ],
        ),
        migrations.CreateModel(
            name='Pal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Fulfillment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.TextField(blank=True)),
                ('pal', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='visits.pal')),
                ('visit', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='visits.visit')),
            ],
        ),
    ]
