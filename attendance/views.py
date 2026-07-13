from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from core.decorators import hr_or_admin_required
from core.models import User
from attendance.models import AttendanceRecord


@login_required
def punch(request):
    today = timezone.localdate()
    record, _ = AttendanceRecord.objects.get_or_create(user=request.user, date=today)

    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.now()
        if action == 'in' and not record.in_time:
            record.in_time = now
            record.save()
            messages.success(request, f"Punched in at {now.strftime('%I:%M %p')}")
        elif action == 'out' and record.in_time and not record.out_time:
            record.out_time = now
            record.save()
            messages.success(request, f"Punched out at {now.strftime('%I:%M %p')}")
        return redirect('attendance:punch')

    my_records = AttendanceRecord.objects.filter(user=request.user)[:30]
    return render(request, 'attendance/punch.html', {'record': record, 'my_records': my_records})


@login_required
def my_attendance(request):
    records = AttendanceRecord.objects.filter(user=request.user)
    return render(request, 'attendance/my_attendance.html', {'records': records})


@hr_or_admin_required
def attendance_reports(request):
    records = AttendanceRecord.objects.select_related('user').all()[:200]
    late_count = AttendanceRecord.objects.filter(is_late=True).count()
    return render(request, 'attendance/reports.html', {'records': records, 'late_count': late_count})


@hr_or_admin_required
def employee_attendance(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    records = AttendanceRecord.objects.filter(user=emp_user)
    return render(request, 'attendance/employee_attendance.html', {'emp_user': emp_user, 'records': records})
