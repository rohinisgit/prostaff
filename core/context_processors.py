from django.db.models import Q
from leaves.models import LeaveRequest, LeaveNotification
from core.models import User


def notifications(request):
    if not request.user.is_authenticated:
         return {}
    user = request.user
     # Badge for "My Leave" / "Permission / Leave" tab — unread status
    # updates on the user's OWN requests (approved/rejected/etc).
    # Disappears once they open that tab (marked read in my_leaves view).
    my_leave_count = LeaveNotification.objects.filter(user=user, is_read=False).count()

    # Badge for "Leave Approvals" / "Leave Requests" tab — items actually
    # waiting on this user's action. Disappears naturally once approved/rejected.
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

    return {'my_leave_count': my_leave_count, 'leave_approval_count': approval_count}
