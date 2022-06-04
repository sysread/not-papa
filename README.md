# TIPS

## Create a super-user account to log into /admin

    python manage.py createsuperuser --username=someone --email=someone@somewhere.com

## Reset database and migrations

    rm -R visits/migrations/0001_initial.py visits/migrations/__pycache__ db.sqlite3
    python manage.py makemigrations
    python manage.py migrate
