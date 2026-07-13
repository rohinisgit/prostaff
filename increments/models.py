from django.db import models
from django.conf import settings


class IncrementRequest(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='increment_requests')
    current_basic = models.DecimalField(max_digits=10, decimal_places=2)
    requested_basic = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='increments_requested')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='increments_approved')
    created_at = models.DateTimeField(auto_now_add=True)

    # The manager HR explicitly picked to give feedback on this increment.
    # Only set (and only required) when the employee's role is EMPLOYEE.
    # Managers and Admins skip feedback entirely — this stays null for them.
    feedback_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='increments_feedback_requested'
    )

    @property
    def increment_percent(self):
        if self.current_basic:
            return round(((self.requested_basic - self.current_basic) / self.current_basic) * 100, 2)
        return 0

    @property
    def needs_feedback(self):
        """Only rank-and-file Employees go through manager feedback.
        Increments for Managers or Admins never need it."""
        return self.user.role == 'EMPLOYEE'

    @property
    def can_be_decided(self):
        """HR can only see Approve/Reject once feedback isn't required at
        all, or once the assigned manager has actually submitted it."""
        if not self.needs_feedback:
            return True
        return hasattr(self, 'feedback') and self.feedback is not None

    def __str__(self):
        return f"Increment for {self.user} ({self.status})"


class IncrementFeedback(models.Model):
    """Feedback the assigned manager gives about an increment under
    consideration. Visible to HR only — never to Admin."""
    SUGGEST = 'SUGGEST'
    NEUTRAL = 'NEUTRAL'
    NOT_SUGGEST = 'NOT_SUGGEST'
    SUGGESTION_CHOICES = [
        (SUGGEST, "Yeah! I suggest increment for this employee"),
        (NEUTRAL, "My suggestion is neutral, this is working normal"),
        (NOT_SUGGEST, "No, I don't suggest — not working hard"),
    ]

    increment_request = models.OneToOneField(IncrementRequest, on_delete=models.CASCADE, related_name='feedback')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='increment_feedbacks_given')
    suggestion = models.CharField(max_length=15, choices=SUGGESTION_CHOICES)
    description = models.TextField(blank=True, help_text="Why do you think so?")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feedback on {self.increment_request} by {self.manager}"

class IncrementCycleSkip(models.Model):
    """When HR clicks "Cancel" on a Due for Annual Increment card, this
    records that decision so the reminder doesn't keep resurfacing for the
    same anniversary. It reappears naturally once that employee actually
    gets an increment (their anniversary date shifts forward)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='increment_skips')
    anniversary_date = models.DateField()
    skipped_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='increment_skips_made')
    skipped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'anniversary_date')

    def __str__(self):
        return f"Skipped increment reminder - {self.user} ({self.anniversary_date})"