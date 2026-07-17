from django.contrib import admin
from queries.models import EmployeeQuery, QueryMessage

admin.site.register(EmployeeQuery)
admin.site.register(QueryMessage)