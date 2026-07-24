from django.db.models import Q


def not_expired_leaves(qs, today):
    """Excludes permission/leave requests whose date (or end date, for
    multi-day leave) has already passed. Used by BOTH the approvals list
    and the notification-badge count so they always agree — otherwise a
    request can inflate the badge while being hidden from the list itself,
    making it impossible to ever clear."""
    return qs.filter(
        Q(request_type='PERMISSION', permission_date__gte=today) |
        Q(request_type='LEAVE', end_date__gte=today)
    )