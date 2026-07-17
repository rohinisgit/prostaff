from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.decorators import hr_only_required, role_required
from core.models import User
from queries.models import EmployeeQuery, QueryMessage
from queries.forms import EmployeeQueryForm, QueryMessageForm


@login_required
def my_queries(request):
    if request.method == 'POST':
        form = EmployeeQueryForm(request.POST, acting_user=request.user)
        if form.is_valid():
            query = form.save(commit=False)
            query.user = request.user
            query.save()
            QueryMessage.objects.create(query=query, sender=request.user, text=query.message)
            messages.success(request, f"Your query has been sent to {query.recipient_user}.")
            return redirect('queries:my_queries')
    else:
        form = EmployeeQueryForm(acting_user=request.user)

    my_queries_qs = EmployeeQuery.objects.filter(user=request.user).select_related('recipient_user')

    users_by_role = {
        'ADMIN': list(User.objects.filter(role='ADMIN').exclude(id=request.user.id).values('id', 'first_name', 'last_name', 'username')),
        'HR': list(User.objects.filter(role='HR').exclude(id=request.user.id).values('id', 'first_name', 'last_name', 'username')),
        'MANAGER': list(User.objects.filter(role='MANAGER').exclude(id=request.user.id).values('id', 'first_name', 'last_name', 'username')),
    }
    for role_users in users_by_role.values():
        for u in role_users:
            u['display'] = (f"{u['first_name']} {u['last_name']}".strip() or u['username'])

    return render(request, 'queries/my_queries.html', {
        'form': form, 'my_queries': my_queries_qs, 'users_by_role': users_by_role,
    })


@login_required
def query_thread(request, query_id):
    query = get_object_or_404(EmployeeQuery.objects.select_related('user', 'recipient_user'), id=query_id)

    if not query.can_be_accessed_by(request.user):
        messages.error(request, "You do not have access to this query.")
        return redirect('core:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'send_message' and query.status == 'OPEN':
            msg_form = QueryMessageForm(request.POST)
            if msg_form.is_valid():
                msg = msg_form.save(commit=False)
                msg.query = query
                msg.sender = request.user
                msg.save()
            return redirect('queries:query_thread', query_id=query.id)
        elif action == 'resolve' and request.user.id == query.user_id and query.status == 'OPEN':
            query.close()
            messages.success(request, "Query marked as resolved.")
            return redirect('queries:query_thread', query_id=query.id)

    msg_form = QueryMessageForm()
    thread_messages = query.messages.select_related('sender')
    is_owner = request.user.id == query.user_id
    can_show_resolve = is_owner and query.status == 'OPEN' and query.recipient_has_replied

    return render(request, 'queries/query_thread.html', {
        'query': query, 'thread_messages': thread_messages, 'msg_form': msg_form,
        'is_owner': is_owner, 'can_show_resolve': can_show_resolve,
    })


@login_required
def delete_query(request, query_id):
    query = get_object_or_404(EmployeeQuery, id=query_id, user=request.user)
    if request.method == 'POST':
        query.delete()
        messages.success(request, "Query deleted.")
    return redirect('queries:my_queries')


def _inbox(request, recipient_role, page_title, manager_only=False):
    status_filter = request.GET.get('status', '')
    if manager_only:
        qs = EmployeeQuery.objects.filter(recipient_role='MANAGER', recipient_user=request.user)
    else:
        qs = EmployeeQuery.objects.filter(recipient_role=recipient_role)
    qs = qs.select_related('user', 'recipient_user')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'queries/query_inbox.html', {
        'queries': qs, 'selected_status': status_filter, 'page_title': page_title,
    })


@hr_only_required
def hr_queries(request):
    return _inbox(request, 'HR', 'Employee Queries — HR')


@role_required('ADMIN')
def admin_queries(request):
    return _inbox(request, 'ADMIN', 'Employee Queries — Admin')


@login_required
def manager_queries(request):
    if not request.user.is_manager():
        messages.error(request, "Only Managers can view this page.")
        return redirect('core:dashboard')
    return _inbox(request, 'MANAGER', 'Employee Queries — My Team', manager_only=True)