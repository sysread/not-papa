import random
import string

import visits.app.account as account


def rstr(size):
    return ''.join(random.choice(string.ascii_letters) for x in range(size))


def new_user(mins=90):
    email = f"{rstr(5)}@{rstr(10)}.com"
    return account.add_new_account(rstr(5), rstr(5), email, "swordfish", mins)
