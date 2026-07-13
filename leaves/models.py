from django.db import models
from django.conf import settings


class LeaveBalance(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_balance')
    cl_balance = models.DecimalField(max_digits=4, decimal_places=1, default=12)
    el_balance = models.DecimalField(max_digits=4, decimal_places=1, default=15)
    sick_balance = models.DecimalField(max_digits=4, decimal_places=1, default=8)

    def __str__(self):
        return f"Leave balance - {self.user}"


class LeaveRequest(models.Model):
    LEAVE_TYPES = [('CL', 'Casual Leave'), ('EL', 'Earned Leave'), ('SICK', 'Sick Leave')]
    STATUS_CHOICES = [
        ('PENDING_MANAGER', 'Pending Manager Approval'),
        ('PENDING_HR', 'Pending HR Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_MANAGER')
    applied_at = models.DateTimeField(auto_now_add=True)

    reviewed_by_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='leaves_manager_reviewed'
    )
    manager_reviewed_at = models.DateTimeField(null=True, blank=True)

    reviewed_by_hr = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='leaves_hr_reviewed'
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)

    @property
    def num_days(self):
        return (self.end_date - self.start_date).days + 1

    def get_manager(self):
        """The manager who should review this at the manager stage. Only
        relevant for non-manager employees — manager-level requests always
        skip straight to HR (see initial_status)."""
        dept = self.user.department
        if dept and dept.manager_id and dept.manager_id != self.user_id:
            return dept.manager
        if self.user.manager_id and self.user.manager.role == 'MANAGER':
            return self.user.manager
        return None

    def initial_status(self):
        """Decide the starting stage when this request is created."""
        if self.user.role == 'MANAGER':
            return 'PENDING_HR'
        if self.get_manager():
            return 'PENDING_MANAGER'
        return 'PENDING_HR'

    def __str__(self):
        return f"{self.user} - {self.leave_type} ({self.status})"