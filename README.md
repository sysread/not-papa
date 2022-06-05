# Design

* User accounts are managed with Django's built in authentication system
* When a user account is registered, both a Pal and Member account are created for it


# TIPS

## Create a super-user account to log into /admin

    python manage.py createsuperuser --username=someone --email=someone@somewhere.com

## Reset database and migrations

    rm -Rf visits/migrations/* db.sqlite3
    python manage.py makemigrations visits
    python manage.py migrate


# FUTURE

* `Member`s' local time zone should be detected by the "visit request" form
* `Member`s' address would be needed to make an actual visit
* Insurance `Plan` model
* All the kinds of security required to make account registration safe
