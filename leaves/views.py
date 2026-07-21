from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from core.models import User
from leaves.models import LeaveRequest, LeaveBalance, LeaveNotification


def _notify(user, leave, message):
    if user is None:
        return
    LeaveNotification.objects.create(user=user, leave_request=leave, message=message)


def _apply_balance_deduction(leave):
    """Only full-day Leave requests draw down a balance. Permission
    requests are hour-based and don't touch the leave balances."""
    if leave.request_type != 'LEAVE':
        return
    balance, _ = LeaveBalance.objects.get_or_create(user=leave.user)
    if leave.leave_type == 'CL':
        balance.cl_balance = max(0, balance.cl_balance - leave.num_days)
    elif leave.leave_type == 'EL':
        balance.el_balance = max(0, balance.el_balance - leave.num_days)
    elif leave.leave_type == 'SICK':
        balance.sick_balance = max(0, balance.sick_balance - leave.num_days)
    balance.save()


@login_required
def my_leaves(request):
    LeaveNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    balance, _ = LeaveBalance.objects.get_or_create(user=request.user)

    other_hrs = None
    if request.user.role == 'HR':
        other_hrs = User.objects.filter(role='HR').exclude(id=request.user.id)

    if request.method == 'POST':
        request_type = request.POST.get('request_type', 'PERMISSION')
        if request_type not in ('PERMISSION', 'LEAVE'):
            request_type = 'PERMISSION'

        leave = LeaveRequest(
            user=request.user,
            request_type=request_type,
            reason=request.POST.get('reason', ''),
        )

        if request_type == 'PERMISSION':
            leave.permission_date = request.POST.get('permission_date') or None
            leave.from_time = request.POST.get('from_time') or None
            leave.to_time = request.POST.get('to_time') or None
            leave.num_hours = request.POST.get('num_hours') or None
            if not leave.permission_date:
                messages.error(request, "Please choose a date for the permission request.")
                return redirect('leaves:my_leaves')
        else:
            leave.leave_type = request.POST.get('leave_type')
            leave.start_date = request.POST.get('start_date') or None
            leave.end_date = request.POST.get('end_date') or None
            if not leave.start_date or not leave.end_date:
                messages.error(request, "Please choose both a start and end date for the leave request.")
                return redirect('leaves:my_leaves')

        if request.user.role == 'HR':
            target_hr_id = request.POST.get('target_hr')
            if not target_hr_id:
                messages.error(request, "Select which HR colleague should review your request.")
                return redirect('leaves:my_leaves')
            leave.target_hr_id = target_hr_id

        leave.status = leave.initial_status()
        leave.save()
        messages.success(request, f"{leave.get_request_type_display()} request submitted.")
        return redirect('leaves:my_leaves')

    requests_qs = LeaveRequest.objects.filter(user=request.user)
    return render(request, 'leaves/my_leaves.html', {
        'balance': balance, 'requests': requests_qs, 'other_hrs': other_hrs,
    })


def _team_managed_by(manager):
    return User.objects.filter(
        Q(department__manager=manager) |
        Q(manager=manager, department__manager__isnull=True)
    ).exclude(id=manager.id).distinct()


@login_required
def leave_approvals(request):
    user = request.user
    today = timezone.localdate()
    # Only show requests whose leave/permission date hasn't passed yet.
    active_leave = (
        Q(request_type='LEAVE', end_date__gte=today) |
        Q(request_type='PERMISSION', permission_date__gte=today)
    )
    context = {'manager_approved_notices': None, 'hr_rejected_pending': None}

    if user.role == 'HR':
        context['requests'] = LeaveRequest.objects.filter(status='PENDING_HR').filter(active_leave).exclude(user=user).filter(
            Q(target_hr__isnull=True) | Q(target_hr=user)
        ).select_related('user', 'user__profile', 'user__department', 'reviewed_by_manager')

        today = timezone.localdate()
        now_time = timezone.localtime().time()

        candidates = LeaveRequest.objects.filter(
            status='APPROVED'
        ).exclude(user=user).select_related('user', 'reviewed_by_manager').order_by('-hr_reviewed_at')[:50]

        still_active = []
        for r in candidates:
            if r.request_type == 'PERMISSION':
                if not r.permission_date or r.permission_date < today:
                    continue
                if r.permission_date == today and r.to_time and now_time > r.to_time:
                    continue
            else:  # LEAVE
                if not r.end_date or r.end_date < today:
                    continue
            still_active.append(r)
            if len(still_active) >= 20:
                break
        context['manager_approved_notices'] = still_active

    elif user.role == 'ADMIN':
        context['requests'] = LeaveRequest.objects.filter(active_leave).select_related(
            'user', 'user__profile', 'user__department', 'reviewed_by_manager', 'reviewed_by_hr', 'target_hr'
        )

    elif user.is_manager():
        team = _team_managed_by(user)
        context['requests'] = LeaveRequest.objects.filter(
            user__in=team, status='PENDING_MANAGER'
        ).filter(active_leave).select_related('user', 'user__profile', 'user__department')

        context['hr_rejected_pending'] = LeaveRequest.objects.filter(
            reviewed_by_manager=user, status='HR_REJECTED_PENDING_MANAGER'
        ).filter(active_leave).select_related('user', 'user__profile', 'user__department')

    else:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('core:dashboard')

    return render(request, 'leaves/approvals.html', context)
@login_required
def review_leave(request, leave_id, decision):
    user = request.user
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    label = leave.get_request_type_display()

    if user.role == 'ADMIN':
        messages.error(request, "Admin has view-only access and cannot approve or reject requests.")
        return redirect('leaves:approvals')

    # ---- Stage 0: manager finalizing a request HR sent back ----
    if leave.status == 'HR_REJECTED_PENDING_MANAGER':
        approving_manager = leave.get_manager()
        if not (user.is_manager() and approving_manager and approving_manager.id == user.id):
            messages.error(request, "You cannot action this request.")
            return redirect('leaves:approvals')

        leave.status = 'REJECTED'
        leave.save()
        _notify(leave.user, leave, f"Your {label.lower()} request was rejected (HR declined it; your manager has finalized the rejection).")
        messages.success(request, f"{label} request rejected for {leave.user}.")
        return redirect('leaves:approvals')

    # ---- Stage 1: manager review ----
    if user.is_manager() and leave.status == 'PENDING_MANAGER':
        approving_manager = leave.get_manager()
        if not approving_manager or approving_manager.id != user.id:
            messages.error(request, "You cannot review this request.")
            return redirect('leaves:approvals')

        leave.reviewed_by_manager = user
        leave.manager_reviewed_at = timezone.now()

        if decision == 'approve':
            leave.status = 'PENDING_HR'
            leave.save()
            messages.success(request, f"{label} approved and forwarded to HR for {leave.user}.")
        else:
            leave.status = 'REJECTED'
            leave.save()
            _notify(leave.user, leave, f"Your {label.lower()} request was rejected by your manager.")
            messages.success(request, f"{label} rejected for {leave.user}.")
        return redirect('leaves:approvals')

    # ---- Stage 2: HR review ----
    if user.role == 'HR' and leave.status == 'PENDING_HR':
        if leave.user_id == user.id:
            messages.error(request, "You cannot approve or reject your own request.")
            return redirect('leaves:approvals')
        if leave.target_hr_id and leave.target_hr_id != user.id:
            messages.error(request, "This request was routed to a different HR colleague.")
            return redirect('leaves:approvals')

        leave.reviewed_by_hr = user
        leave.hr_reviewed_at = timezone.now()

        if decision == 'approve':
            leave.status = 'APPROVED'
            leave.save()
            _apply_balance_deduction(leave)
            _notify(leave.user, leave, f"Your {label.lower()} request was approved by HR.")
            if leave.reviewed_by_manager_id:
                _notify(leave.reviewed_by_manager, leave, f"HR approved {leave.user}'s {label.lower()} request.")
            messages.success(request, f"{label} approved for {leave.user}.")
        else:
            if leave.requires_manager_finalization:
                # A manager already approved this — send it back to them to
                # finalize the rejection rather than rejecting it outright.
                leave.status = 'HR_REJECTED_PENDING_MANAGER'
                leave.save()
                _notify(leave.reviewed_by_manager, leave, f"HR rejected {leave.user}'s {label.lower()} request. Please finalize the rejection.")
                messages.info(request, f"Sent back to {leave.reviewed_by_manager} to finalize the rejection.")
            else:
                leave.status = 'REJECTED'
                leave.save()
                _notify(leave.user, leave, f"Your {label.lower()} request was rejected by HR.")
                messages.success(request, f"{label} rejected for {leave.user}.")
        return redirect('leaves:approvals')

    messages.error(request, "You cannot review this request.")
    return redirect('core:dashboard')


@login_required
def notifications(request):
    notes = list(
        LeaveNotification.objects.filter(user=request.user)
        .select_related('leave_request', 'leave_request__user')[:50]
    )
    LeaveNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'leaves/notifications.html', {'notes': notes})