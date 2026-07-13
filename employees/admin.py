from django.contrib import admin
from employees.models import EmployeeProfile, EmployeeDocument, ResignationRequest

admin.site.register(EmployeeProfile)
admin.site.register(EmployeeDocument)
admin.site.register(ResignationRequest)