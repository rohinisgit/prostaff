from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q

from core.forms import StyledAuthenticationForm
from attendance.models import AttendanceRecord
from leaves.models import LeaveRequest
from employees.models import EmployeeProfile


class HRLoginView(auth_views.LoginView):
    template_name = 'core/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}

    today = timezone.localdate()
    context['today_record'] = AttendanceRecord.objects.filter(user=user, date=today).first()

    if user.role == 'ADMIN':
        context['hr_count'] = EmployeeProfile.objects.filter(user__role='HR').count()
        context['manager_count'] = EmployeeProfile.objects.filter(user__role='MANAGER').count()
        context['employee_count'] = EmployeeProfile.objects.filter(user__role='EMPLOYEE').count()

    elif user.role == 'HR':
        base_qs = EmployeeProfile.objects.exclude(user__role__in=['HR', 'ADMIN'])
        context['total_employees'] = base_qs.count()

        active_qs = base_qs.filter(status='ACTIVE')
        context['active_employees'] = active_qs.count()
        context['inactive_employees'] = base_qs.filter(status='ONBOARDING').count()
        context['exited_employees'] = base_qs.filter(status='EXITED').count()

        active_user_ids = list(active_qs.values_list('user_id', flat=True))

        present_ids = set(AttendanceRecord.objects.filter(
            date=today, in_time__isnull=False, user_id__in=active_user_ids
        ).values_list('user_id', flat=True))

        on_leave_ids = set(LeaveRequest.objects.filter(
            status='APPROVED', user_id__in=active_user_ids
        ).filter(
            Q(permission_date=today) | Q(start_date__lte=today, end_date__gte=today)
        ).values_list('user_id', flat=True))

        total_active = len(active_user_ids)
        present_count = len(present_ids)
        on_leave_count = len(on_leave_ids - present_ids)
        absent_count = max(0, total_active - present_count - on_leave_count)

        context['present_today'] = present_count
        context['on_leave_today'] = on_leave_count
        context['absent_today'] = absent_count

    else:
        month_start = today.replace(day=1)
        context['month_attendance'] = AttendanceRecord.objects.filter(
            user=user, date__gte=month_start, date__lte=today
        ).count()
        context['my_pending_leaves'] = LeaveRequest.objects.filter(user=user, status='PENDING').count()
        if user.is_manager():
            context['team_size'] = user.team_members.exclude(id=user.id).count()

    return render(request, 'core/dashboard.html', context)