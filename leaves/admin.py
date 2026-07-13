from django.contrib import admin
from leaves.models import LeaveRequest, LeaveBalance

admin.site.register(LeaveRequest)
admin.site.register(LeaveBalance)
