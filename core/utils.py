def get_active_branch(request):
    """The Branch currently being viewed.
    - Admins and HR flagged can_access_all_branches can switch freely;
      their choice is remembered in the session.
    - Everyone else (regular HR, Managers, Employees) is locked to their
      own assigned branch — no switcher, no override."""
    from core.models import Branch

    user = request.user
    can_switch = user.is_authenticated and (
        user.role == 'ADMIN' or (user.role == 'HR' and user.can_access_all_branches)
    )

    if not can_switch:
        return getattr(user, 'branch', None)

    branch_id = request.session.get('active_branch_id')
    if branch_id:
        branch = Branch.objects.filter(id=branch_id).first()
        if branch:
            return branch

    return user.branch or Branch.objects.first()


def user_can_switch_branch(user):
    return user.is_authenticated and (
        user.role == 'ADMIN' or (user.role == 'HR' and user.can_access_all_branches)
    )