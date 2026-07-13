from django.contrib import admin
from attendance.models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'in_time', 'out_time', 'total_hours', 'is_late')
    list_filter = ('is_late', 'date')
