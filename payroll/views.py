import calendar
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse

from core.decorators import hr_or_admin_required, hr_only_required
from core.models import User
from payroll.models import PayrollRun, Payslip, SalaryStructure
from payroll.forms import SalaryStructureForm
from payroll.utils import compute_payslip_for_user, generate_payslip_pdf


def _month_bounds(year, month):
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def _recent_months(today, count=6):
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append((f"{year:04d}-{month:02d}", date(year, month, 1).strftime('%B %Y')))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months


@login_required
def my_payslips(request):
    if request.user.role in ('ADMIN', 'HR'):
        payslips = Payslip.objects.filter(user=request.user).select_related('payroll_run')
    else:
        payslips = Payslip.objects.filter(user=request.user, is_released=True).select_related('payroll_run')
    return render(request, 'payroll/my_payslips.html', {'payslips': payslips})


@login_required
def download_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)
    is_owner = payslip.user == request.user
    is_hr_or_admin = request.user.is_hr_or_admin()

    if not (is_owner or is_hr_or_admin):
        messages.error(request, "You cannot access this payslip.")
        return redirect('core:dashboard')

    if is_owner and not is_hr_or_admin and not payslip.is_released:
        messages.error(request, "This payslip hasn't been released yet.")
        return redirect('payroll:my_payslips')

    if not payslip.pdf_file:
        generate_payslip_pdf(payslip)
    return FileResponse(payslip.pdf_file.open('rb'), as_attachment=True, filename=payslip.pdf_file.name)


@hr_or_admin_required
def payroll_runs(request):
    role_order = ['ADMIN', 'MANAGER', 'EMPLOYEE', 'HR']
    role_labels = {'ADMIN': 'Admin', 'MANAGER': 'Managers', 'EMPLOYEE': 'Employees', 'HR': 'HR'}

    all_users = User.objects.exclude(id=request.user.id).select_related('department')
    months = _recent_months(timezone.localdate())

    # Build a map of user_id -> set of "YYYY-MM" month keys that already have
    # a released (credited) payslip, so the template can swap the
    # "Credit Salary" button for a green "Salary Credited" badge per month.
    released_payslips = Payslip.objects.filter(
        is_released=True, user__in=all_users
    ).select_related('payroll_run')
    credited_map = {}
    for p in released_payslips:
        key = p.payroll_run.start_date.strftime('%Y-%m')
        credited_map.setdefault(p.user_id, set()).add(key)

    sections = []
    for role in role_order:
        role_employees = all_users.filter(role=role).order_by('first_name', 'username')
        if not role_employees.exists():
            continue
        employees_list = [
            {
                'user': emp,
                'credited_months': ','.join(sorted(credited_map.get(emp.id, set()))),
            }
            for emp in role_employees
        ]
        sections.append({'role': role, 'role_label': role_labels[role], 'employees': employees_list})

    return render(request, 'payroll/runs.html', {'sections': sections, 'months': months})


@hr_or_admin_required
def employee_payroll_history(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    payslips = Payslip.objects.filter(user=emp_user).select_related('payroll_run').order_by('-payroll_run__start_date')
    has_salary_structure = SalaryStructure.objects.filter(user=emp_user).exists()
    months = _recent_months(timezone.localdate())

    credited_months = ','.join(sorted({
        p.payroll_run.start_date.strftime('%Y-%m') for p in payslips if p.is_released
    }))

    return render(request, 'payroll/employee_payroll_history.html', {
        'emp_user': emp_user, 'payslips': payslips,
        'has_salary_structure': has_salary_structure, 'months': months,
        'credited_months': credited_months,
    })


@hr_only_required
def credit_salary(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        month_value = request.POST.get('month', '')
        try:
            year, month = (int(part) for part in month_value.split('-'))
            start_date, end_date = _month_bounds(year, month)
        except (ValueError, AttributeError):
            messages.error(request, "Please select a valid month.")
            return redirect('payroll:employee_payroll_history', user_id=emp_user.id)

        if not SalaryStructure.objects.filter(user=emp_user).exists():
            messages.error(request, f"{emp_user} has no salary structure set up. Set one up first.")
            return redirect('payroll:employee_payroll_history', user_id=emp_user.id)

        run, _ = PayrollRun.objects.get_or_create(
            start_date=start_date, end_date=end_date, defaults={'processed_by': request.user},
        )
        payslip = compute_payslip_for_user(emp_user, run)
        if not payslip:
            messages.error(request, f"Could not generate a payslip for {emp_user}.")
            return redirect('payroll:employee_payroll_history', user_id=emp_user.id)

        payslip.is_released = True
        payslip.released_by = request.user
        payslip.released_at = timezone.now()
        payslip.save()
        generate_payslip_pdf(payslip)

        messages.success(request, f"Salary credited to {emp_user} for {start_date.strftime('%B %Y')}.")

    return redirect('payroll:employee_payroll_history', user_id=emp_user.id)


@hr_or_admin_required
def salary_structures(request):
    structures = SalaryStructure.objects.select_related('user')
    return render(request, 'payroll/salary_structures.html', {'structures': structures})


@hr_only_required
def edit_salary_structure(request, user_id):
    emp_user = get_object_or_404(User, id=user_id)
    structure, _ = SalaryStructure.objects.get_or_create(user=emp_user, defaults={'basic': 0})
    if request.method == 'POST':
        form = SalaryStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary structure saved.')
            return redirect('payroll:salary_structures')
    else:
        form = SalaryStructureForm(instance=structure)
    return render(request, 'payroll/edit_salary_structure.html', {'emp_user': emp_user, 'structure': structure, 'form': form})