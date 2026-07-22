def get_active_branch(request):
    from core.models import Branch

    user = request.user
    can_switch = user_can_switch_branch(user)

    if not can_switch:
        return getattr(user, 'branch', None)

    branch_id = request.session.get('active_branch_id')
    if branch_id:
        if user.role == 'ADMIN':
            branch = Branch.objects.filter(id=branch_id).first()
        else:
            branch = user.accessible_branches.filter(id=branch_id).first()
        if branch:
            return branch

    if user.role == 'ADMIN':
        return user.branch or Branch.objects.first()
    return user.branch or user.accessible_branches.first()


def user_can_switch_branch(user):
    if not user.is_authenticated:
        return False
    if user.role == 'ADMIN':
        return True
    if user.role == 'HR':
        return user.accessible_branches.exists()
    return False