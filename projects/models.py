from django.db import models
from django.conf import settings
from django.utils import timezone


class Project(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    requirements_file = models.FileField(upload_to='project_requirements/', null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_projects')
    lead = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='led_projects')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='proposed_projects')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Completion workflow: a Manager marks a project as successfully
    # completed once the work is done. Completed projects get their own
    # section on the projects list, regardless of their dates.
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects_completed'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def phase(self):
        """Buckets a project into COMPLETED / ACTIVE / UPCOMING for the
        projects list. COMPLETED is a manual, explicit action by a Manager.
        UPCOMING means the start date hasn't arrived yet. Everything else
        (already started, or no start date set) is ACTIVE."""
        if self.status == 'COMPLETED':
            return 'COMPLETED'
        if self.start_date and self.start_date > timezone.localdate():
            return 'UPCOMING'
        return 'ACTIVE'

    def __str__(self):
        return self.name


class ProjectAssignment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_assignments')
    role_on_project = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} on {self.project}"


class ProjectSubmission(models.Model):
    """A progress/completion update the project lead sends to the manager
    for review. The manager can approve it or send it back with corrections."""
    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('NEEDS_CORRECTION', 'Needs Correction'),
        ('APPROVED', 'Approved'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_submissions')
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to='project_submissions/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    submitted_at = models.DateTimeField(auto_now_add=True)

    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='project_submissions_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Update on {self.project} by {self.submitted_by} ({self.status})"