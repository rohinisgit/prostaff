from django.contrib import admin
from leaves.models import LeaveRequest, LeaveBalance, LeaveNotification

admin.site.register(LeaveRequest)
admin.site.register(LeaveBalance)
admin.site.register(LeaveNotification)