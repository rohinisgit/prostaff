from django.db.models import Q
from leaves.models import LeaveRequest
from core.models import User, Branch
from core.utils import get_active_branch, user_can_switch_branch


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    if user.role in ('ADMIN', 'HR'):
        count = LeaveRequest.objects.filter(status='PENDING_HR').count()
    elif user.is_manager():
        team = User.objects.filter(
            Q(department__manager=user) |
            Q(manager=user, department__manager__isnull=True)
        ).exclude(id=user.id).distinct()
        count = LeaveRequest.objects.filter(user__in=team, status='PENDING_MANAGER').count()
    else:
        count = LeaveRequest.objects.filter(user=user, status__in=['PENDING_MANAGER', 'PENDING_HR']).count()
    return {'notification_count': count}

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