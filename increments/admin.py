from django.contrib import admin
from increments.models import IncrementRequest, IncrementFeedback, IncrementCycleSkip

admin.site.register(IncrementRequest)
admin.site.register(IncrementFeedback)
admin.site.register(IncrementCycleSkip)