# DESIGN NOTES

## BEHAVIOR

* When a user account is registered, both a `Pal` and `Member` account are created for it, since the requirements suggest that members may double as pals and can earn extra visit time by fulfilling appointments for other members
* "Banked" minutes are tracked via `MinuteLedger`
  * Both credits and debits live together in the table as positive and negative amounts, respectively
  * Entries are linked to the underlying `User` account, since each `User` has both a `Member` and `Pal` account
* When a `Member` requests a `Visit`, a debit is added to their `MinuteLedger`
* When a `Pal` accepts a `Visit`, a `Fulfillment` is created
* Cancelling a `Visit` will also cancel any associated `Fulfillment`s and `MinuteLedger`s
* Cancelling a `Fulfillment` makes the `Visit` visible again to other `Pal`s for scheduling
* When a `Pal` completes a `Fulfillment`, a credit is added to their `MinuteLedger`, less our 15% cut

## TECH

* Python and Django are (in theory) fairly readable, even for non-pythonistas
* `User` accounts are managed with Django's built in authentication system
* Bootstrap is easy to set up and familiar enough that using it for a simple UI reduces the number of variables in building this project


# INSTALL

## Requirements

  * Python3 (aliased to `python` in example commands below)
  * sqlite3 (django defaults to sqlite for simple dev setup)

## Install django and dependencies

    $ python -m pip install Django django-crispy-forms

## Check out the repo and init the database

    $ git clone https://github.com/sysread/not-papa.git
    $ cd not-papa
    $ python manage.py migrate

## Run the web service

    $ python manage.py runserver

## Run the test suite

    $ python manage.py test visits

### Verbosely:

    $ python manage.py test -v2

### In parallel:

    $ python manage.py test --parallel=4

# TIPS

## Create a super-user account to log into `/admin`

    python manage.py createsuperuser --username=someone --email=someone@somewhere.com

## View SQL generated by ORM

Django provides some easy mechanisms for viewing the SQL generated by the ORM
for a query as well as the query's execution plan.

Wherever you see a query, e.g.:

    # From visits.views.list_visits()
    query = request.user.member.visit_set.order_by("-when").filter(cancelled=False)

You can print the generated SQL out to view in the server log output:

    print(query.query)

As well as the execution plan:

    print(query.explain())


# FUTURE

* `User`s' time zones should be detected and used to control the display of dates and times on relevant pages
* "Request a visit" form should have a usable date/time picker widget
* `Member`s' address would be needed to schedule and make an actual visit
* Insurance `Plan` model that includes the number of plan minutes
* All the kinds of security required to make account registration safe
* On the member's visits list, convert individual forms into a FormSet so we don't lose error messages on failed cancelations
* Paginate the list of completed visits when displaying a member's visits
* Segregate list of visits by status, with incomplete visits in ascending order, but completed visits in descending order
* Profile page with transaction history and minutes balances
* Cron job to cancel visits which never get accepted by a pal and notify the member
* `Visit`s show names when `Pal` has visited the `Member` in the past
* Validation to ensure the same account does not fulfill its own visits
