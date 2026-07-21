from urllib import request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from increments.models import IncrementRequest
from core.decorators import admin_only_required

from core.decorators import hr_or_admin_required, hr_only_required, hr_admin_or_manager_required
from core.models import User
from attendance.models import AttendanceRecord
from employees.models import EmployeeProfile, EmployeeDocument, ResignationRequest, BankDetail
from employees.forms import (
    EmployeeSelfEditForm, NewEmployeeForm, HRDocumentForm, SelfDocumentForm,
    RoleChangeForm, ResignationRequestForm, HREmployeeEditForm,
    EmployeeIdentityForm, BankDetailForm,
)
from employees.id_utils import (
    generate_enrollment_id, generate_employee_id,
    enrollment_prefix_for_branch, employee_id_prefix_for_branch, split_id,
)
from payroll.models import SalaryStructure
from payroll.forms import SalaryStructureForm
from django.urls import reverse
from payroll.models import SalaryStructure
from increments.models import IncrementRequest
from core.utils import get_active_branch, user_can_switch_branch
from core.decorators import role_required


def _present_user_ids_today():
    today = timezone.localdate()
    return set(
        AttendanceRecord.objects.filter(date=today, in_time__isnull=False).values_list('user_id', flat=True)
    )


def _can_apply_resignation(user):
    return user.role in ('EMPLOYEE', 'MANAGER', 'ADMIN')


def _can_edit_identity(acting_user, emp_user):
    """HR and Admin can edit anyone (except HR can't touch other HR/Admin
    role changes elsewhere — unrelated to this). A Manager can only edit
    members of their own department, and never themselves."""
    if acting_user.role in ('HR', 'ADMIN'):
        return True
    if acting_user.is_manager():
        return emp_user.department_id is not None and emp_user.department_id == acting_user.department_id and emp_user.id != acting_user.id
    return False


def _department_sort_key(dept_name):
    """Data Entry departments first, then Software, then everything else
    alphabetically."""
    lower = dept_name.lower()
    if 'data entry' in lower:
        priority = 0
    elif 'software' in lower:
        priority = 1
    else:
        priority = 2
    return (priority, lower)


@login_required
def my_profile(request):
    profile, _ = EmployeeProfile.objects.get_or_create(user=request.user)
    bank_detail, _ = BankDetail.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = EmployeeSelfEditForm(request.POST, request.FILES, instance=profile, user_instance=request.user)
        bank_form = BankDetailForm(request.POST, instance=bank_detail)
        if form.is_valid() and bank_form.is_valid():
            form.save()
            bank_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('employees:my_profile')
        else:
            messages.error(request, 'Please fix the highlighted fields below.')
    else:
        form = EmployeeSelfEditForm(instance=profile, user_instance=request.user)
        bank_form = BankDetailForm(instance=bank_detail)

    documents = request.user.documents.all()
    doc_form = SelfDocumentForm()
    pending_resignation = ResignationRequest.objects.filter(
        user=request.user, status__in=['PENDING', 'NEGOTIATING']
    ).order_by('-submitted_at').first()

    return render(request, 'employees/my_profile.html', {
        'form': form, 'bank_form': bank_form, 'documents': documents, 'doc_form': doc_form, 'profile': profile,
        'bank_detail': bank_detail,
        'can_apply_resignation': _can_apply_resignation(request.user),
        'pending_resignation': pending_resignation,
    })


@login_required
def upload_own_document(request):
    if request.method == 'POST':
        form = SelfDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, 'Document uploaded.')
        else:
            messages.error(request, 'Please choose a valid document type and file.')
    return redirect('employees:my_profile')


@login_required
def delete_own_document(request, doc_id):
    """Lets an employee remove one of their own uploaded documents — e.g.
    to replace an outdated Aadhar scan with a fresh upload."""
    doc = get_object_or_404(EmployeeDocument, id=doc_id, user=request.user)
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document deleted. You can upload a new one below.')
    return redirect('employees:my_profile')


@hr_only_required
def delete_document(request, user_id, doc_id):
    """HR-side equivalent of delete_own_document, for official documents
    HR uploaded on an employee's behalf."""
    emp_user = get_object_or_404(User, id=user_id)
    doc = get_object_or_404(EmployeeDocument, id=doc_id, user=emp_user)
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document deleted.')
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)


@login_required
def apply_resignation(request):
    if not _can_apply_resignation(request.user):
        messages.error(request, "You do not have permission to view this page.")
        return redirect('core:dashboard')

    if ResignationRequest.objects.filter(user=request.user, status='PENDING').exists():
        messages.info(request, "You already have a resignation request pending HR's review.")
        return redirect('employees:my_profile')

    if request.method == 'POST':
        form = ResignationRequestForm(request.POST)
        if form.is_valid():
            resignation = form.save(commit=False)
            resignation.user = request.user
            resignation.save()
            messages.success(request, "Your resignation request has been submitted to HR.")
            return redirect('employees:my_profile')
    else:
        form = ResignationRequestForm()

    return render(request, 'employees/apply_resignation.html', {'form': form})


@hr_or_admin_required
def resignation_list(request):
    resignations = ResignationRequest.objects.select_related('user').all()
    return render(request, 'employees/resignation_list.html', {'resignations': resignations})


@hr_only_required
def approve_resignation(request, resignation_id):
    resignation = get_object_or_404(ResignationRequest, id=resignation_id)
    if resignation.status != 'PENDING':
        messages.error(request, "This resignation cannot be approved at this stage.")
        return redirect('employees:resignation_list')

    if request.method == 'POST':
        custom_days = request.POST.get('custom_days')
        try:
            days = int(custom_days) if custom_days else int(request.POST.get('notice_period_days', 30))
        except ValueError:
            messages.error(request, "Enter a valid number of days.")
            return redirect('employees:resignation_list')

        if days < 0:
            messages.error(request, "Notice period cannot be negative.")
            return redirect('employees:resignation_list')

        # approve() sets profile.status='EXITED', exit_date and exit_reason.
        # The employee immediately shows up as Exited in the HR/Admin
        # directory (and to their Manager, on their team page).
        resignation.approve(hr_user=request.user, notice_period_days=days)
        messages.success(
            request,
            f"Resignation approved for {resignation.user}. Notice period: {days} days. Exit date: {resignation.exit_date}."
        )
    return redirect('employees:resignation_list')


@hr_only_required
def reject_resignation(request, resignation_id):
    resignation = get_object_or_404(ResignationRequest, id=resignation_id)
    if resignation.status != 'PENDING':
        messages.error(request, "This resignation cannot be rejected at this stage.")
        return redirect('employees:resignation_list')

    if request.method == 'POST':
        resignation.reject(hr_user=request.user)
        messages.info(request, f"Resignation rejected for {resignation.user}.")
    return redirect('employees:resignation_list')


@hr_only_required
def negotiate_resignation(request, resignation_id):
    resignation = get_object_or_404(ResignationRequest, id=resignation_id)
    if resignation.status != 'PENDING':
        messages.error(request, "You can only negotiate while the request is pending.")
        return redirect('employees:resignation_list')

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if not message:
            messages.error(request, "Write a message before sending.")
            return redirect('employees:resignation_list')
        resignation.send_negotiation(hr_user=request.user, message=message)
        messages.success(request, f"Your message has been sent to {resignation.user}.")
    return redirect('employees:resignation_list')


@login_required
def accept_resignation_offer(request, resignation_id):
    resignation = get_object_or_404(ResignationRequest, id=resignation_id, user=request.user)
    if resignation.status != 'NEGOTIATING':
        messages.error(request, "There is no active offer to accept.")
        return redirect('employees:my_profile')

    if request.method == 'POST':
        resignation.accept_offer()
        messages.success(request, "You've accepted HR's offer. Your resignation has been withdrawn.")
    return redirect('employees:my_profile')


@login_required
def quit_after_negotiation(request, resignation_id):
    resignation = get_object_or_404(ResignationRequest, id=resignation_id, user=request.user)
    if resignation.status != 'NEGOTIATING':
        messages.error(request, "There is no active offer to respond to.")
        return redirect('employees:my_profile')

    if request.method == 'POST':
        resignation.quit_anyway(message=request.POST.get('message', ''))
        messages.success(request, "Your response has been sent to HR. They'll confirm your notice period shortly.")
    return redirect('employees:my_profile')

@hr_only_required
def onboard_employee(request):
    active_branch = get_active_branch(request)
    if request.method == 'POST':
        form = NewEmployeeForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if not user_can_switch_branch(request.user):
                user.branch = request.user.branch
            user.set_password(form.cleaned_data['password'])
            department = form.cleaned_data.get('department')
            if department and department.manager_id and user.role != User.ROLE_MANAGER:
                user.manager = department.manager
            else:
                user.manager = None

            # Auto-generate the branch-prefixed Employee ID (SPSB0#-####).
            user.employee_id = generate_employee_id(user.branch)
            user.save()

            profile = EmployeeProfile.objects.create(user=user, status='ONBOARDING')
            # Auto-generate the branch-prefixed Enrollment ID (TRB0#-####).
            profile.enrollment_id = generate_enrollment_id(user.branch)
            profile.save()
            BankDetail.objects.get_or_create(user=user)

            messages.success(request, f'{user} onboarded successfully (Employee ID {user.employee_id}, Enrollment ID {profile.enrollment_id}). Share their login credentials securely.')
            return redirect('employees:employee_detail', user_id=user.id)
    else:
        initial = {}
        if active_branch and not user_can_switch_branch(request.user):
            initial['branch'] = active_branch.id
        form = NewEmployeeForm(initial=initial)
    return render(request, 'employees/onboard.html', {'form': form, 'locked_branch': not user_can_switch_branch(request.user)})

@role_required('ADMIN')
def toggle_branch_admin_access(request, user_id):
    emp_user = get_object_or_404(User, id=user_id, role='HR')
    if request.method == 'POST':
        emp_user.can_access_all_branches = not emp_user.can_access_all_branches
        emp_user.save()
        state = "granted" if emp_user.can_access_all_branches else "revoked"
        messages.success(request, f"All-branch access {state} for {emp_user}.")
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)


@hr_or_admin_required
def employee_directory(request):
    query = request.GET.get('q', '')
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')

    employees = User.objects.exclude(id=request.user.id).select_related('department', 'profile')

    if request.user.role == 'HR':
        employees = employees.exclude(role__in=['HR', 'ADMIN'])
        active_branch = get_active_branch(request)
    if active_branch:
        employees = employees.filter(branch=active_branch)

    if query:
        employees = employees.filter(
            Q(first_name__icontains=query) |
            Q(username__icontains=query) |
            Q(employee_id__icontains=query)
        )

    if department_filter:
        if department_filter == 'No Department':
            employees = employees.filter(department__isnull=True)
        else:
            employees = employees.filter(department__name=department_filter)

    employees = list(employees)

    base_qs = User.objects.exclude(id=request.user.id).exclude(profile__status='ONBOARDING')
    if request.user.role == 'HR':
        base_qs = base_qs.exclude(role__in=['HR', 'ADMIN'])
    if active_branch:
        base_qs = base_qs.filter(branch=active_branch)
    dept_qs = base_qs.select_related('department')
    dept_names = sorted(
        {emp.department.name for emp in dept_qs if emp.department},
        key=_department_sort_key,
    )
    has_no_dept = base_qs.filter(department__isnull=True).exists()
    departments = dept_names + (['No Department'] if has_no_dept else [])

    # Exited employees are always included here (no status exclusion above
    # other than ONBOARDING for the department-list computation) — HR and
    # Admin can always see who's exited, filterable via the Status dropdown.
    employee_rows = []
    for emp in employees:
        profile = getattr(emp, 'profile', None)
        if profile and profile.status == 'EXITED':
            emp_status = 'EXITED'
        elif profile and profile.status == 'ONBOARDING':
            emp_status = 'ONBOARD'
        else:
            emp_status = 'ACTIVE'

        if status_filter and status_filter != emp_status:
            continue
        emp.display_status = emp_status
        employee_rows.append(emp)

    employee_rows.sort(key=lambda emp: (
        _department_sort_key(emp.department.name if emp.department else 'zzz_no_department'),
        (emp.first_name or emp.username).lower(),
    ))

    return render(request, 'employees/directory.html', {
        'employees': employee_rows,
        'query': query,
        'departments': departments,
        'selected_department': department_filter,
        'selected_status': status_filter,
    })
@hr_admin_or_manager_required
def employee_detail(request, user_id):
    """HR/Admin/Manager view. Read-only by default. HR/Admin/the employee's
    Manager can toggle Edit mode (?edit=1). Admin never edits anywhere else
    in the system, but per the HR identity-data policy Admin *can* edit the
    extended identity/bank fields from here, same as HR and Manager."""
    emp_user = get_object_or_404(User, id=user_id)

    if request.user.role == 'HR' and emp_user.role == 'ADMIN':
        messages.error(request, "You do not have permission to view this account.")
        return redirect('employees:directory')

    if request.user.is_manager() and request.user.role not in ('HR', 'ADMIN'):
        if emp_user.department_id != request.user.department_id:
            messages.error(request, "You can only view profiles of your own department's staff.")
            return redirect('employees:my_department')

    profile, _ = EmployeeProfile.objects.get_or_create(user=emp_user)
    bank_detail, _ = BankDetail.objects.get_or_create(user=emp_user)
    documents = emp_user.documents.all()
    doc_form = HRDocumentForm()
    role_form = RoleChangeForm(instance=emp_user, acting_user=request.user)
    latest_resignation = ResignationRequest.objects.filter(user=emp_user).first()

    salary_structure = SalaryStructure.objects.filter(user=emp_user).first()

    # Increment info shown directly in the Salary Details card. Queried
    # fresh on every load, so it reflects the latest state the moment HR
    # approves a new increment — no extra sync step needed.
    increments_qs = IncrementRequest.objects.filter(user=emp_user, status='APPROVED').order_by('-effective_date')
    increment_count = increments_qs.count()
    latest_increment = increments_qs.first()

    can_edit_identity = _can_edit_identity(request.user, emp_user)
    edit_mode = can_edit_identity and request.GET.get('edit') == '1'

    return render(request, 'employees/employee_detail.html', {
        'emp_user': emp_user, 'profile': profile, 'bank_detail': bank_detail,
        'documents': documents, 'doc_form': doc_form,
        'role_form': role_form, 'latest_resignation': latest_resignation,
        'salary_structure': salary_structure,
        'increment_count': increment_count, 'latest_increment': latest_increment,
        'edit_mode': edit_mode, 'can_edit_identity': can_edit_identity,
    })


@hr_only_required
def update_employee_status(request, user_id):
    """HR moves an employee between Onboarding, Active, and Exited directly
    from the Edit page. Moving EXITED -> ACTIVE (a rejoin) automatically
    preserves their prior joining date in old_joining_date so it isn't
    lost once date_joined_company is updated for the new stint."""
    emp_user = get_object_or_404(User, id=user_id)
    profile, _ = EmployeeProfile.objects.get_or_create(user=emp_user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ('ONBOARDING', 'ACTIVE', 'EXITED'):
            if new_status == 'ACTIVE' and profile.status == 'EXITED' and not profile.old_joining_date:
                profile.old_joining_date = emp_user.date_joined_company
            profile.status = new_status
            profile.save()
            messages.success(request, f"{emp_user}'s status changed to {profile.get_status_display()}.")
        else:
            messages.error(request, "Invalid status selected.")
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)

@hr_only_required
def upload_document(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = HRDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = emp_user
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, 'Document uploaded.')
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)


@hr_admin_or_manager_required
def edit_employee_profile(request, user_id):
    """Editable view — profile fields, extended identity fields, bank
    details, status, role & access, salary, and document uploads all live
    here. Reachable by HR, Admin, or the employee's own Manager."""
    emp_user = get_object_or_404(User, id=user_id)

    if not _can_edit_identity(request.user, emp_user):
        messages.error(request, "You do not have permission to edit this profile.")
        return redirect('employees:employee_detail', user_id=emp_user.id)

    profile, _ = EmployeeProfile.objects.get_or_create(user=emp_user)
    bank_detail, _ = BankDetail.objects.get_or_create(user=emp_user)

    enrollment_prefix = enrollment_prefix_for_branch(emp_user.branch)
    employee_id_prefix = employee_id_prefix_for_branch(emp_user.branch)

    if request.method == 'POST':
        form = HREmployeeEditForm(request.POST, instance=emp_user)
        identity_form = EmployeeIdentityForm(request.POST, instance=profile)
        bank_form = BankDetailForm(request.POST, instance=bank_detail)

        # Enrollment ID / Employee ID: the UI only lets HR edit the numeric
        # suffix; the branch prefix is re-attached here server-side so it
        # can never be spoofed to a different branch's prefix.
        enrollment_suffix = request.POST.get('enrollment_suffix', '').strip()
        employee_id_suffix = request.POST.get('employee_id_suffix', '').strip()

        if form.is_valid() and identity_form.is_valid() and bank_form.is_valid():
            user_obj = form.save(commit=False)
            if employee_id_suffix:
                user_obj.employee_id = f"{employee_id_prefix}{employee_id_suffix}"
            user_obj.save()

            profile_obj = identity_form.save(commit=False)
            if enrollment_suffix:
                profile_obj.enrollment_id = f"{enrollment_prefix}{enrollment_suffix}"
            profile_obj.save()

            bank_form.save()

            messages.success(request, f"{emp_user}'s profile has been updated.")
            return redirect('employees:edit_employee_profile', user_id=emp_user.id)
        else:
            messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = HREmployeeEditForm(instance=emp_user)
        identity_form = EmployeeIdentityForm(instance=profile)
        bank_form = BankDetailForm(instance=bank_detail)

    documents = emp_user.documents.all()
    doc_form = HRDocumentForm()
    role_form = RoleChangeForm(instance=emp_user, acting_user=request.user)
    salary_structure, _ = SalaryStructure.objects.get_or_create(user=emp_user, defaults={'basic': 0})
    salary_form = SalaryStructureForm(instance=salary_structure)

    return render(request, 'employees/edit_employee_profile.html', {
        'emp_user': emp_user, 'form': form, 'identity_form': identity_form, 'bank_form': bank_form,
        'documents': documents, 'doc_form': doc_form, 'role_form': role_form,
        'profile': profile, 'bank_detail': bank_detail, 'salary_form': salary_form,
        'is_admin_viewer': request.user.role == 'ADMIN',
        'can_change_role': request.user.role == 'HR',
        'enrollment_prefix': enrollment_prefix,
        'employee_id_prefix': employee_id_prefix,
        'enrollment_suffix': split_id(profile.enrollment_id, enrollment_prefix),
        'employee_id_suffix': split_id(emp_user.employee_id, employee_id_prefix),
    })


@hr_or_admin_required
def change_role(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)

    if request.user.role == 'ADMIN':
        messages.error(request, "Admin has view-only access and cannot change roles.")
        return redirect('employees:employee_detail', user_id=emp_user.id)
    if emp_user == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect('employees:edit_employee_profile', user_id=emp_user.id)
    if emp_user.role == 'ADMIN':
        messages.error(request, "Admin accounts are top priority and their role cannot be changed.")
        return redirect('employees:edit_employee_profile', user_id=emp_user.id)
    if request.user.role == 'HR' and emp_user.role in ('HR', 'ADMIN'):
        messages.error(request, "HR cannot change the role of an HR or Admin account.")
        return redirect('employees:edit_employee_profile', user_id=emp_user.id)

    if request.method == 'POST':
        form = RoleChangeForm(request.POST, instance=emp_user, acting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{emp_user}'s role changed to {emp_user.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selection.")
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)


@hr_only_required
def delete_employee(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    if emp_user == request.user:
        messages.error(request, "You Cannot delete you own account")
        return redirect('employees:directory')

    profile, _ = EmployeeProfile.objects.get_or_create(user=emp_user)
    if profile.status != 'EXITED':
        messages.error(request, "This employee can only be deleted after their resignation has been accepted.")
        return redirect('employees:employee_detail', user_id=emp_user.id)

    if request.method == 'POST':
        name = str(emp_user)
        emp_user.delete()
        messages.success(request, f"{name} has been removed from the system")
        return redirect('employees:directory')
    return render(request, 'employees/confirm_delete.html', {'emp_user': emp_user})


@hr_only_required
def update_salary_structure(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    structure, _ = SalaryStructure.objects.get_or_create(user=emp_user, defaults={'basic': 0})
    if request.method == 'POST':
        form = SalaryStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary structure saved.')
        else:
            messages.error(request, 'Please fix the highlighted salary fields.')
    return redirect('employees:edit_employee_profile', user_id=emp_user.id)


@login_required
def my_department(request):
    if not request.user.is_manager():
        messages.error(request, "Only managers can view this page.")
        return redirect('core:dashboard')

    staff = list(
        User.objects.filter(
            department=request.user.department,
            branch=request.user.branch,
        ).exclude(id=request.user.id).select_related('profile')
    )
    present_user_ids = _present_user_ids_today()
    for s in staff:
        s.is_present_today = s.id in present_user_ids
    return render(request, 'employees/my_department.html', {'staff': staff, 'department': request.user.department})

@login_required
def team_member_detail(request, user_id):
    if not request.user.is_manager():
        messages.error(request, "Only managers can view this page.")
        return redirect('core:dashboard')

    emp_user = get_object_or_404(User, id=user_id, department=request.user.department, branch=request.user.branch, )
    if emp_user.id == request.user.id:
        messages.error(request, "You cannot view your own team member page.")
        return redirect('employees:my_department')

    profile, _ = EmployeeProfile.objects.get_or_create(user=emp_user)
    records = AttendanceRecord.objects.filter(user=emp_user)[:30]

    today = timezone.localdate()
    is_onboarding = profile.status == 'ONBOARDING'
    is_present_today = AttendanceRecord.objects.filter(
        user=emp_user, date=today, in_time__isnull=False
    ).exists()

    return render(request, 'employees/team_member_detail.html', {
        'emp_user': emp_user, 'profile': profile, 'records': records,
        'is_onboarding': is_onboarding, 'is_present_today': is_present_today,
    })

@login_required
def my_resignation(request):
    if not _can_apply_resignation(request.user):
        messages.error(request, "You do not have permission to view this page.")
        return redirect('core:dashboard')

    resignations = ResignationRequest.objects.filter(user=request.user).order_by('-submitted_at')
    pending_resignation = resignations.filter(status__in=['PENDING', 'NEGOTIATING']).first()

    return render(request, 'employees/my_resignation.html', {
        'resignations': resignations,
        'pending_resignation': pending_resignation,
    })


@admin_only_required
def onboard_hr(request):
    if request.method == 'POST':
        form = NewEmployeeForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.ROLE_HR
            user.manager = None
            user.save()
            EmployeeProfile.objects.create(user=user, status='ACTIVE')
            messages.success(request, f'{user} onboarded as HR successfully.')
            return redirect('employees:employee_detail', user_id=user.id)
    else:
        form = NewEmployeeForm(initial={'role': 'HR'})
    return render(request, 'employees/onboard_hr.html', {'form': form})