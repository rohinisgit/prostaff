from django.urls import path
from payroll import views

app_name = 'payroll'

urlpatterns = [
    path('me/', views.my_payslips, name='my_payslips'),
    path('download/<int:payslip_id>/', views.download_payslip, name='download_payslip'),
    path('runs/', views.payroll_runs, name='runs'),
    path('employee/<int:user_id>/', views.employee_payroll_history, name='employee_payroll_history'),
    path('employee/<int:user_id>/credit/', views.credit_salary, name='credit_salary'),
    path('structures/', views.salary_structures, name='salary_structures'),
    path('structures/<int:user_id>/edit/', views.edit_salary_structure, name='edit_salary_structure'),
]