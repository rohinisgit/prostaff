from django.db import models
from django.conf import settings
from django.utils import timezone


class EmployeeQuery(models.Model):
    """A query an employee raises to a specific person (chosen by role,
    then by name). Conversation happens via QueryMessage. Only the
    employee who raised it can mark it Resolved — and only once the
    recipient has replied at least once."""
    RECIPIENT_ADMIN = 'ADMIN'
    RECIPIENT_HR = 'HR'
    RECIPIENT_MANAGER = 'MANAGER'
    RECIPIENT_CHOICES = [
        (RECIPIENT_ADMIN, 'Admin'),
        (RECIPIENT_HR, 'HR'),
        (RECIPIENT_MANAGER, 'Manager'),
    ]

    STATUS_OPEN = 'OPEN'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Resolved'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='queries_raised')
    recipient_role = models.CharField(max_length=10, choices=RECIPIENT_CHOICES)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='queries_received',
        help_text="The specific person this query was sent to."
    )
    message = models.TextField(help_text="The original query message.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def recipient_has_replied(self):
        """Any message from someone other than the raiser counts as the
        recipient side having responded — since HR/Admin queues are
        shared, not just the originally-chosen person."""
        return self.messages.exclude(sender_id=self.user_id).exists()

    def close(self):
        self.status = self.STATUS_CLOSED
        self.closed_at = timezone.now()
        self.save()

    def can_be_accessed_by(self, acting_user):
        if acting_user.id == self.user_id:
            return True
        if self.recipient_role == 'HR' and acting_user.role == 'HR':
            return True
        if self.recipient_role == 'ADMIN' and acting_user.role == 'ADMIN':
            return True
        if self.recipient_role == 'MANAGER' and self.recipient_user_id == acting_user.id:
            return True
        return False

    def __str__(self):
        return f"Query from {self.user} to {self.recipient_user} ({self.status})"


class QueryMessage(models.Model):
    query = models.ForeignKey(EmployeeQuery, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='query_messages_sent')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender} on query #{self.query_id}"