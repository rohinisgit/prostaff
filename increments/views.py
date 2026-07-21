from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from core.utils import get_active_branch

from core.decorators import hr_or_admin_required, hr_only_required
from core.models import User
from employees.models import EmployeeProfile
from increments.models import IncrementRequest, IncrementFeedback, IncrementCycleSkip
from increments.forms import IncrementRequestForm, IncrementFeedbackForm
from payroll.models import SalaryStructure


def _add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Feb 29 landing on a non-leap year
        return d.replace(month=2, day=28, year=d.year + years)


def _last_increment_date(user):
    """The date their pay was last actually increased, or their joining
    date if they've never had one — this is the baseline for the next
    one-year anniversary."""
    last = IncrementRequest.objects.filter(user=user, status='APPROVED').order_by('-effective_date').first()
    if last:
        return last.effective_date
    return user.date_joined_company


@hr_or_admin_required
def increment_list(request):
    today = timezone.localdate()

    all_requests = IncrementRequest.objects.select_related(
        'user', 'feedback_manager', 'approved_by'
    ).prefetch_related('feedback').order_by('-created_at')

    # ---------- Section 1: Active Increment Requests ----------
    # One card per employee — their most recent pending request — newest first.
    seen_users = set()
    in_progress = []
    for inc in all_requests.filter(status='PENDING'):
        if inc.user_id in seen_users:
            continue
        seen_users.add(inc.user_id)
        in_progress.append(inc)
    pending_user_ids = {inc.user_id for inc in in_progress}

    # ---------- Section 2: Due for Annual Increment ----------
    window_end = today + timedelta(days=30)
    active_profiles = EmployeeProfile.objects.filter(
        status='ACTIVE'
    ).exclude(user_id__in=pending_user_ids).select_related('user')

    due_soon = []
    for profile in active_profiles:
        user = profile.user
        base_date = _last_increment_date(user)
        if not base_date:
            continue
        anniversary = _add_years(base_date, 1)
        if anniversary > window_end:
            continue
        if IncrementCycleSkip.objects.filter(user=user, anniversary_date=anniversary).exists():
            continue
        try:
            current_basic = user.salary_structure.basic
        except SalaryStructure.DoesNotExist:
            current_basic = 0
        due_soon.append({
            'user': user,
            'anniversary_date': anniversary,
            'days_left': (anniversary - today).days,
            'last_increment_date': base_date,
            'current_basic': current_basic,
        })
    due_soon.sort(key=lambda d: d['anniversary_date'])

    # ---------- Section 3: Increment History (collapsed by default) ----------
    history_by_user = {}
    for inc in all_requests.exclude(status='PENDING'):
        entry = history_by_user.setdefault(inc.user_id, {'user': inc.user, 'increments': [], 'latest': inc})
        entry['increments'].append(inc)
    history_cards = sorted(history_by_user.values(), key=lambda h: h['latest'].created_at, reverse=True)

    just_completed = None
    confirm_id = request.GET.get('confirm')
    if confirm_id:
        just_completed = IncrementRequest.objects.filter(id=confirm_id).select_related('user').first()

    return render(request, 'increments/list.html', {
        'in_progress': in_progress,
        'due_soon': due_soon,
        'history_cards': history_cards,
        'just_completed': just_completed,
    })

@hr_only_required
def create_increment(request):
    preset_user_id = request.GET.get('user')
    active_branch = get_active_branch(request)

    if request.method == 'POST':
        form = IncrementRequestForm(request.POST, acting_user=request.user, branch=active_branch)
        # ... rest unchanged
    else:
        initial = {}
        if preset_user_id:
            initial['user'] = preset_user_id
        form = IncrementRequestForm(acting_user=request.user, branch=active_branch, initial=initial)

    users_qs = User.objects.exclude(id=request.user.id)
    if active_branch:
        users_qs = users_qs.filter(branch=active_branch)
    user_roles_json = {str(u.id): u.role for u in users_qs}
    return render(request, 'increments/create.html', {'form': form, 'user_roles_json': user_roles_json})

@hr_only_required
def approve_increment(request, increment_id):
    increment = get_object_or_404(IncrementRequest, id=increment_id)
    if not increment.can_be_decided:
        messages.error(request, f"Waiting on feedback from {increment.feedback_manager} before this can be approved.")
        return redirect('increments:list')

    increment.status = 'APPROVED'
    increment.approved_by = request.user
    increment.save()

    structure, _ = SalaryStructure.objects.get_or_create(user=increment.user, defaults={'basic': 0})
    structure.basic = increment.requested_basic
    structure.save()

    IncrementCycleSkip.objects.filter(user=increment.user).delete()
    return redirect(f"{reverse('increments:list')}?confirm={increment.id}")


@hr_only_required
def reject_increment(request, increment_id):
    increment = get_object_or_404(IncrementRequest, id=increment_id)
    if not increment.can_be_decided:
        messages.error(request, f"Waiting on feedback from {increment.feedback_manager} before this can be rejected.")
        return redirect('increments:list')

    increment.status = 'REJECTED'
    increment.approved_by = request.user
    increment.save()
    messages.info(request, f"Increment rejected for {increment.user}.")
    return redirect('increments:list')


@hr_only_required
def dismiss_due_increment(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        anniversary_str = request.POST.get('anniversary_date', '')
        try:
            y, m, d = (int(p) for p in anniversary_str.split('-'))
            IncrementCycleSkip.objects.get_or_create(
                user=emp_user, anniversary_date=date(y, m, d),
                defaults={'skipped_by': request.user},
            )
            messages.info(request, f"Dismissed the increment reminder for {emp_user} this cycle.")
        except (ValueError, TypeError):
            messages.error(request, "Something went wrong dismissing that reminder.")
    return redirect('increments:list')


@hr_or_admin_required
def increment_history_detail(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    increments = IncrementRequest.objects.filter(
        user=emp_user
    ).exclude(status='PENDING').select_related(
        'approved_by', 'feedback_manager', 'requested_by'
    ).prefetch_related('feedback').order_by('-effective_date')
    return render(request, 'increments/history_detail.html', {'emp_user': emp_user, 'increments': increments})


@login_required
def manager_feedback_list(request):
    if not request.user.is_manager():
        messages.error(request, "Only Managers can view this page.")
        return redirect('core:dashboard')

    increments = IncrementRequest.objects.filter(
        status='PENDING', feedback_manager=request.user
    ).select_related('user').prefetch_related('feedback')
    return render(request, 'increments/manager_feedback_list.html', {'increments': increments})


@login_required
def submit_increment_feedback(request, increment_id):
    increment = get_object_or_404(IncrementRequest, id=increment_id)

    if not request.user.is_manager() or increment.feedback_manager_id != request.user.id:
        messages.error(request, "You cannot give feedback for this employee.")
        return redirect('increments:manager_feedback_list')

    existing_feedback = IncrementFeedback.objects.filter(increment_request=increment).first()

    if request.method == 'POST':
        form = IncrementFeedbackForm(request.POST, instance=existing_feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.increment_request = increment
            feedback.manager = request.user
            feedback.save()
            messages.success(request, f"Feedback submitted for {increment.user}. Only HR will see it.")
            return redirect('increments:manager_feedback_list')
    else:
        form = IncrementFeedbackForm(instance=existing_feedback)

    return render(request, 'increments/submit_feedback.html', {'form': form, 'increment': increment})