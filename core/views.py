from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q

from core.forms import StyledAuthenticationForm
from attendance.models import AttendanceRecord
from leaves.models import LeaveRequest
from employees.models import EmployeeProfile
from django.contrib import messages
from core.utils import get_active_branch, user_can_switch_branch
from core.models import Branch




class HRLoginView(auth_views.LoginView):
    template_name = 'core/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

@login_required
def set_active_branch(request):
    if request.method == 'POST':
        user = request.user
        can_switch = user_can_switch_branch(user)
        if not can_switch:
            messages.error(request, "You do not have permission to switch branches.")
            return redirect('core:dashboard')
        branch_id = request.POST.get('branch_id')
        if branch_id:
            allowed = Branch.objects.all() if user.role == 'ADMIN' else user.accessible_branches.all()
            branch = allowed.filter(id=branch_id).first()
            if branch:
                request.session['active_branch_id'] = branch_id
                messages.success(request, f"You are now viewing {branch.name} ({branch.code}).")
            else:
                messages.error(request, "You don't have access to that branch.")
        return redirect(request.POST.get('next') or 'core:dashboard')
    return redirect('core:dashboard')

@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}

    today = timezone.localdate()
    context['today_record'] = AttendanceRecord.objects.filter(user=user, date=today).first()

    active_branch = get_active_branch(request)   # <-- moved above the if/elif, computed once for every role

    if user.role == 'ADMIN':
        base_qs = EmployeeProfile.objects.filter(status='ACTIVE').select_related('user')
        if active_branch:
            base_qs = base_qs.filter(user__branch=active_branch)
        context['hr_count'] = base_qs.filter(user__role='HR').count()
        context['manager_count'] = base_qs.filter(user__role='MANAGER').count()
        context['employee_count'] = base_qs.filter(user__role='EMPLOYEE').count()

    elif user.role == 'HR':
        base_qs = EmployeeProfile.objects.exclude(user__role__in=['HR', 'ADMIN'])
        if active_branch:
            base_qs = base_qs.filter(user__branch=active_branch)
        context['total_employees'] = base_qs.count()
        context['active_employees'] = base_qs.filter(status='ACTIVE').count()

    else:
        month_start = today.replace(day=1)
        context['month_attendance'] = AttendanceRecord.objects.filter(
            user=user, date__gte=month_start, date__lte=today
        ).count()
        context['my_pending_leaves'] = LeaveRequest.objects.filter(user=user, status='PENDING').count()
        if user.is_manager():
            context['team_size'] = user.team_members.exclude(id=user.id).count()

    return render(request, 'core/dashboard.html', context)