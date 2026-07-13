from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

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
        # Admin sees HR / Manager / Employee counts broken out separately.
        # Admin is never counted in any of these.
        context['hr_count'] = EmployeeProfile.objects.filter(user__role='HR').count()
        context['manager_count'] = EmployeeProfile.objects.filter(user__role='MANAGER').count()
        context['employee_count'] = EmployeeProfile.objects.filter(user__role='EMPLOYEE').count()

    elif user.role == 'HR':
        # HR sees everyone except HR and Admin.
        # Total Employees counts everyone regardless of status (Onboarding,
        # Active, or Exited) — the dedicated "View Onboarding" list is where
        # new hires who haven't actually joined yet are tracked separately.
        base_qs = EmployeeProfile.objects.exclude(user__role__in=['HR', 'ADMIN'])
        context['total_employees'] = base_qs.count()
        context['active_employees'] = base_qs.filter(status='ACTIVE').count()

    else:
        month_start = today.replace(day=1)
        context['month_attendance'] = AttendanceRecord.objects.filter(
            user=user, date__gte=month_start, date__lte=today
        ).count()
        context['my_pending_leaves'] = LeaveRequest.objects.filter(user=user, status='PENDING').count()
        if user.is_manager():
            # Manager sees the size of their team, excluding themself.
            context['team_size'] = user.team_members.exclude(id=user.id).count()

    return render(request, 'core/dashboard.html', context)