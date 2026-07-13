from django.db.models import Q
from leaves.models import LeaveRequest
from core.models import User


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    if user.role in ('ADMIN', 'HR'):
        # Only manager-level requests need HR action.
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