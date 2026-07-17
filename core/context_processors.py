from django.db.models import Q
from leaves.models import LeaveRequest, LeaveNotification
from core.models import User
from employees.models import ResignationRequest

def notifications(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    my_leave_count = LeaveNotification.objects.filter(user=user, is_read=False).count()

    approval_count = 0
    if user.role == 'HR':
        approval_count = LeaveRequest.objects.filter(status='PENDING_HR').count()
    elif user.is_manager():
        team = User.objects.filter(
            Q(department__manager=user) |
            Q(manager=user, department__manager__isnull=True)
        ).exclude(id=user.id).distinct()
        approval_count = LeaveRequest.objects.filter(user__in=team, status='PENDING_MANAGER').count()
        approval_count += LeaveRequest.objects.filter(reviewed_by_manager=user, status='HR_REJECTED_PENDING_MANAGER').count()

    has_applied_resignation = ResignationRequest.objects.filter(user=user).exists()

    return {
        'my_leave_count': my_leave_count,
        'leave_approval_count': approval_count,
        'has_applied_resignation': has_applied_resignation,
    }