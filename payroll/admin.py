from django.contrib import admin
from payroll.models import SalaryStructure, PayrollRun, Payslip

admin.site.register(SalaryStructure)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
