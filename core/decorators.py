from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """Restrict a view to users whose .role is in `roles`."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("You do not have permission to view this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def hr_or_admin_required(view_func):
    """View-only pages: HR and Admin can both open these."""
    return role_required('ADMIN', 'HR')(view_func)


def hr_only_required(view_func):
    """Real actions (approve/reject/onboard/etc). Admin is view-only in this
    system, so Admin gets redirected back with a friendly message instead of
    a hard 403."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != 'HR':
            messages.error(request, "Admin has view-only access. Only HR can perform this action.")
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped