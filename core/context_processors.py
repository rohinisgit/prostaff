# core/context_processors.py
from django.utils import timezone
from leaves.models import LeaveRequest
from leaves.utils import not_expired_leaves
from core.models import User, Branch
from core.utils import get_active_branch, user_can_switch_branch, get_manager_team
from leaves.utils import not_expired_leaves


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    today = timezone.localdate()
    if user.role in ('ADMIN', 'HR'):
        active_branch = get_active_branch(request)
        leave_qs = LeaveRequest.objects.filter(status='PENDING_HR').exclude(user=user)
        if active_branch:
            leave_qs = leave_qs.filter(user__branch=active_branch)
        leave_approval_count = leave_qs.count()
        return {
            'leave_approval_count': leave_approval_count,
            'notification_count': leave_approval_count,
        }
    elif user.is_manager():
        team = get_manager_team(user)
        leave_approval_count = LeaveRequest.objects.filter(
            user__in=team, status='PENDING_MANAGER'
        ).count()
        my_leave_count = LeaveRequest.objects.filter(
            user=user, status__in=['PENDING_MANAGER', 'PENDING_HR']
        ).count()
        return {
            'leave_approval_count': leave_approval_count,
            'my_leave_count': my_leave_count,
            'notification_count': leave_approval_count + my_leave_count,
        }
    else:
        my_leave_count = LeaveRequest.objects.filter(
            user=user, status__in=['PENDING_MANAGER', 'PENDING_HR']
        ).count()
        return {
            'my_leave_count': my_leave_count,
            'notification_count': my_leave_count,
        }
def branch_context(request):
    if not request.user.is_authenticated:
        return {}
    can_switch = user_can_switch_branch(request.user)
    branch_order = ['B01', 'B02', 'B03', 'B04']  # Chennai, Thindivanam, Kancheepuram, Madurai
    branches = list(Branch.objects.all())
    branches.sort(key=lambda b: branch_order.index(b.code) if b.code in branch_order else 99)
    return {
        'active_branch': get_active_branch(request),
        'can_switch_branch': can_switch,
        'all_branches': branches if can_switch else [],
    }