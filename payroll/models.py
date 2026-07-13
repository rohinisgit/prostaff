from django.db import models
from django.conf import settings


class SalaryStructure(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='salary_structure')
    basic = models.DecimalField(max_digits=10, decimal_places=2)
    hra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Flat monthly bonus, added on top of earned gross, not prorated by attendance.")
    pf_applicable = models.BooleanField(default=True)
    pf_percent = models.DecimalField(max_digits=4, decimal_places=2, default=12.00)

    @property
    def gross(self):
        return self.basic + self.hra + self.other_allowances

    def __str__(self):
        return f"Salary structure - {self.user}"


class PayrollRun(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='payroll_runs')

    def __str__(self):
        return f"Payroll {self.start_date} - {self.end_date}"


class Payslip(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='payslips')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payslips')

    # Snapshot of the salary structure at the time this payslip was computed.
    basic = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    days_present = models.IntegerField(default=0)
    total_hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pf_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='payslips/', null=True, blank=True)

    # Release workflow: HR must explicitly release a payslip before the
    # employee/manager can see or download it.
    is_released = models.BooleanField(default=False)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='payslips_released')
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('payroll_run', 'user')

    def __str__(self):
        return f"Payslip - {self.user} ({self.payroll_run})"