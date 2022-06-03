from django.contrib import admin

import visits.models


admin.site.register(visits.models.Pal)
admin.site.register(visits.models.Member)
admin.site.register(visits.models.Visit)
admin.site.register(visits.models.Fulfillment)
