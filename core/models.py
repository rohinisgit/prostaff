from django.contrib.auth.models import AbstractUser
from django.db import models
from core.validators import COUNTRY_CODES


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    manager = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='managed_departments'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_ADMIN = 'ADMIN'
    ROLE_HR = 'HR'
    ROLE_MANAGER = 'MANAGER'
    ROLE_EMPLOYEE = 'EMPLOYEE'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_HR, 'HR'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_EMPLOYEE, 'Employee'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='employees')
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='team_members')
    date_joined_company = models.DateField(null=True, blank=True)

    # Phone is now stored as exactly 10 digits, with the country code kept
    # separately so numbers can be validated and displayed consistently.
    phone_country_code = models.CharField(max_length=5, choices=COUNTRY_CODES, default='+91')
    phone = models.CharField(max_length=10, blank=True)

    def is_hr_or_admin(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_HR)

    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    def __str__(self):
        return self.get_full_name() or self.username