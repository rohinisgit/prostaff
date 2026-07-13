from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from core.models import User
from leaves.models import LeaveRequest, LeaveBalance


def _apply_balance_deduction(leave):
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
    balance, _ = LeaveBalance.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        leave = LeaveRequest(
            user=request.user,
            leave_type=request.POST.get('leave_type'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            reason=request.POST.get('reason', ''),
        )
        leave.status = leave.initial_status()
        leave.save()
        messages.success(request, 'Leave request submitted.')
        return redirect('leaves:my_leaves')
    requests_qs = LeaveRequest.objects.filter(user=request.user)
    return render(request, 'leaves/my_leaves.html', {'balance': balance, 'requests': requests_qs})


def _team_managed_by(manager):
    return User.objects.filter(
        Q(department__manager=manager) |
        Q(manager=manager, department__manager__isnull=True)
    ).exclude(id=manager.id).distinct()


@login_required
def leave_approvals(request):
    user = request.user
    context = {}

    if user.role == 'HR':
        # Actionable: manager-level leave requests waiting on HR, PLUS any
        # other HR colleague's own leave request. An HR user's OWN request
        # never appears here — they are not allowed to approve/reject it
        # themselves; another HR user handles it instead.
        context['requests'] = LeaveRequest.objects.filter(status='PENDING_HR').exclude(user=user).select_related('user')
        # Informational only: employee leaves already finalized by their manager.
        context['manager_approved_notices'] = LeaveRequest.objects.filter(
            status='APPROVED', reviewed_by_manager__isnull=False
        ).exclude(user__role='MANAGER').select_related('user', 'reviewed_by_manager').order_by('-manager_reviewed_at')[:20]

    elif user.role == 'ADMIN':
        context['requests'] = LeaveRequest.objects.select_related('user').all()
        context['manager_approved_notices'] = None

    elif user.is_manager():
        team = _team_managed_by(user)
        context['requests'] = LeaveRequest.objects.filter(user__in=team, status='PENDING_MANAGER').select_related('user')
        context['manager_approved_notices'] = None

    else:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('core:dashboard')

    return render(request, 'leaves/approvals.html', context)


@login_required
def review_leave(request, leave_id, decision):
    user = request.user
    leave = get_object_or_404(LeaveRequest, id=leave_id)

    if user.role == 'ADMIN':
        messages.error(request, "Admin has view-only access and cannot approve or reject leave requests.")
        return redirect('leaves:approvals')

    # Manager stage: manager's decision is FINAL for employee leave requests.
    if user.is_manager() and leave.status == 'PENDING_MANAGER':
        approving_manager = leave.get_manager()
        if not approving_manager or approving_manager.id != user.id:
            messages.error(request, "You cannot review this leave request.")
            return redirect('leaves:approvals')

        leave.reviewed_by_manager = user
        leave.manager_reviewed_at = timezone.now()

        if decision == 'approve':
            leave.status = 'APPROVED'
            leave.save()
            _apply_balance_deduction(leave)
            messages.success(request, f"Leave approved for {leave.user}. HR has been notified.")
        else:
            leave.status = 'REJECTED'
            leave.save()
            messages.success(request, f"Leave rejected for {leave.user}.")
        return redirect('leaves:approvals')

    # HR stage: used for a Manager's own leave request (or the rare
    # no-manager-assigned case), and also for another HR colleague's own
    # leave request. An HR user can never review their own request, even
    # if they reach this URL directly.
    if user.role == 'HR' and leave.status == 'PENDING_HR':
        if leave.user_id == user.id:
            messages.error(request, "You cannot approve or reject your own leave request. Another HR team member needs to review it.")
            return redirect('leaves:approvals')

        leave.reviewed_by_hr = user
        leave.hr_reviewed_at = timezone.now()
        leave.status = 'APPROVED' if decision == 'approve' else 'REJECTED'
        leave.save()

        if leave.status == 'APPROVED':
            _apply_balance_deduction(leave)

        messages.success(request, f"Leave {'approved' if leave.status == 'APPROVED' else 'rejected'} for {leave.user}.")
        return redirect('leaves:approvals')

    messages.error(request, "You cannot review this leave request.")
    return redirect('core:dashboard')