from decimal import Decimal
from django.db.models import Sum
from attendance.models import AttendanceRecord
from payroll.models import SalaryStructure, Payslip
from attendance.utils import compute_authorized_hours_for_range

STANDARD_DAILY_HOURS = Decimal('8')


def compute_payslip_for_user(user, payroll_run):
    """Computes and persists a Payslip for `user` for the given PayrollRun.
    Pay is based on actual hours worked (from AttendanceRecord.total_hours),
    not just days present — this handles half-days, early punch-outs, etc.
    PF is prorated to the same earned ratio, so a Non-PF employee (pf_applicable=False)
    simply gets pf_deduction=0 throughout."""
    try:
        structure = user.salary_structure
    except SalaryStructure.DoesNotExist:
        return None

    attendance = AttendanceRecord.objects.filter(
        user=user, date__gte=payroll_run.start_date, date__lte=payroll_run.end_date
    )
    days_present = attendance.exclude(in_time__isnull=True).count()
    
    total_hours_worked = compute_authorized_hours_for_range(user, payroll_run.start_date, payroll_run.end_date)

    total_days_in_cycle = (payroll_run.end_date - payroll_run.start_date).days + 1
    gross = structure.gross

    if total_days_in_cycle > 0 and gross > 0:
        per_day_gross = gross / Decimal(total_days_in_cycle)
        per_hour_rate = per_day_gross / STANDARD_DAILY_HOURS
        gross_pay = round(per_hour_rate * total_hours_worked, 2)
        # An employee can't be paid more than the full cycle's gross even if
        # their logged hours somehow exceed the standard expectation.
        if gross_pay > gross:
            gross_pay = gross
        earned_ratio = gross_pay / gross
    else:
        gross_pay = Decimal('0.00')
        earned_ratio = Decimal('0.00')

    pf_deduction = Decimal('0.00')
    if structure.pf_applicable:
        full_cycle_pf = structure.basic * (structure.pf_percent / Decimal('100'))
        pf_deduction = round(full_cycle_pf * earned_ratio, 2)

    bonus = structure.bonus or Decimal('0.00')
    net_pay = gross_pay + bonus - pf_deduction

    payslip, _ = Payslip.objects.update_or_create(
        payroll_run=payroll_run,
        user=user,
        defaults={
            'basic': structure.basic,
            'hra': structure.hra,
            'allowances': structure.other_allowances,
            'bonus': bonus,
            'days_present': days_present,
            'total_hours_worked': total_hours_worked,
            'gross_pay': gross_pay,
            'pf_deduction': pf_deduction,
            'other_deductions': Decimal('0.00'),
            'net_pay': net_pay,
        }
    )
    return payslip


def generate_payslip_pdf(payslip):
    """Generates a detailed PDF payslip using ReportLab and attaches it to the payslip."""
    import io
    from reportlab.pdfgen import canvas
    from django.core.files.base import ContentFile

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, "Payslip")
    p.setFont("Helvetica", 11)
    y = 775
    p.drawString(50, y, f"Employee: {payslip.user.get_full_name() or payslip.user.username}"); y -= 15
    p.drawString(50, y, f"Employee ID: {payslip.user.employee_id or '-'}"); y -= 15
    p.drawString(50, y, f"Pay Period: {payslip.payroll_run.start_date} to {payslip.payroll_run.end_date}"); y -= 25

    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Earnings"); y -= 18
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Basic: Rs. {payslip.basic}"); y -= 15
    p.drawString(50, y, f"HRA: Rs. {payslip.hra}"); y -= 15
    p.drawString(50, y, f"Other Allowances: Rs. {payslip.allowances}"); y -= 15
    p.drawString(50, y, f"Bonus: Rs. {payslip.bonus}"); y -= 15
    p.drawString(50, y, f"Days Present: {payslip.days_present}"); y -= 15
    p.drawString(50, y, f"Total Hours Worked: {payslip.total_hours_worked}"); y -= 15
    p.drawString(50, y, f"Earned Gross Pay: Rs. {payslip.gross_pay}"); y -= 25

    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Deductions"); y -= 18
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"PF Deduction: Rs. {payslip.pf_deduction}"); y -= 15
    p.drawString(50, y, f"Other Deductions: Rs. {payslip.other_deductions}"); y -= 25

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, f"Net Pay: Rs. {payslip.net_pay}")

    p.showPage()
    p.save()
    buffer.seek(0)

    filename = f"payslip_{payslip.user.username}_{payslip.payroll_run.id}.pdf"
    payslip.pdf_file.save(filename, ContentFile(buffer.read()), save=True)
    return payslip.pdf_file