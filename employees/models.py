from django.db import models
from django.conf import settings
from django.utils import timezone
from core.validators import COUNTRY_CODES
from datetime import timedelta



class EmployeeProfile(models.Model):
    STATUS_CHOICES = [
        ('ONBOARDING', 'Onboarding'),
        ('ACTIVE', 'Active'),
        ('EXITED', 'Exited'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    designation = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    bank_account = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    pan_no = models.CharField(max_length=20, blank=True)
    aadhar_no = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_country_code = models.CharField(max_length=5, choices=COUNTRY_CODES, default='+91')
    emergency_contact_phone = models.CharField(max_length=10, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    # Status now only ever changes via two automated workflows: HR marking
    # onboarding complete (ONBOARDING -> ACTIVE), and HR accepting a
    # resignation request (-> EXITED, see ResignationRequest.accept()).
    # HR never edits this field directly on the employee detail page.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ONBOARDING')

    # Only ever set by ResignationRequest.accept() below.
    exit_date = models.DateField(null=True, blank=True)
    exit_reason = models.TextField(blank=True)

    def __str__(self):
        return str(self.user)


class EmployeeDocument(models.Model):
    OFFER = 'OFFER'
    APPOINTMENT = 'APPOINTMENT'
    DEGREE = 'DEGREE'
    PAN_CARD = 'PAN_CARD'
    AADHAR_CARD = 'AADHAR_CARD'
    ID_PROOF = 'ID_PROOF'
    EXPERIENCE = 'EXPERIENCE'
    OTHER = 'OTHER'

    DOC_TYPES = [
        (OFFER, 'Offer Letter'),
        (APPOINTMENT, 'Appointment Letter'),
        (DEGREE, 'Degree Certificate'),
        (PAN_CARD, 'PAN Card'),
        (AADHAR_CARD, 'Aadhar Card'),
        (ID_PROOF, 'ID Proof'),
        (EXPERIENCE, 'Experience Letter'),
        (OTHER, 'Other'),
    ]

    # HR may only ever upload these — official, company-issued letters.
    HR_DOC_TYPES = [OFFER, APPOINTMENT]
    # Everyone uploads these to their own profile — HR cannot upload
    # personal documents on someone else's behalf.
    SELF_DOC_TYPES = [DEGREE, PAN_CARD, AADHAR_CARD, ID_PROOF, EXPERIENCE, OTHER]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    file = models.FileField(upload_to='employee_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='uploaded_documents')

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.user}"

class ResignationRequest(models.Model):
    """Employee/Manager/Admin submits just a reason. HR then approves
    (setting the notice period), rejects, or negotiates. If HR negotiates,
    the employee can accept the offer (withdrawing) or confirm they still
    want to quit, which sends it back to HR to allot a notice period."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending HR Review'),
        ('NEGOTIATING', 'HR Sent an Offer'),
        ('ACCEPTED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn (Offer Accepted)'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resignation_requests')
    reason = models.TextField(help_text="Reason for resigning.")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Only ever set by HR, at approval time.
    notice_period_days = models.PositiveIntegerField(null=True, blank=True)
    exit_date = models.DateField(null=True, blank=True)

    # HR's negotiation offer.
    hr_message = models.TextField(blank=True)
    hr_message_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='resignation_offers_sent')
    hr_message_at = models.DateTimeField(null=True, blank=True)

    # Employee's reply, only used if they decline the offer and quit anyway.
    employee_reply = models.TextField(blank=True)
    employee_replied_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='resignations_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def approve(self, hr_user, notice_period_days):
        self.notice_period_days = notice_period_days
        self.exit_date = timezone.localdate() + timedelta(days=notice_period_days)
        self.status = 'ACCEPTED'
        self.reviewed_by = hr_user
        self.reviewed_at = timezone.now()
        self.save()

        profile, _ = EmployeeProfile.objects.get_or_create(user=self.user)
        profile.status = 'EXITED'
        profile.exit_date = self.exit_date
        profile.exit_reason = self.reason
        profile.save()

    def reject(self, hr_user):
        self.status = 'REJECTED'
        self.reviewed_by = hr_user
        self.reviewed_at = timezone.now()
        self.save()

    def send_negotiation(self, hr_user, message):
        self.status = 'NEGOTIATING'
        self.hr_message = message
        self.hr_message_by = hr_user
        self.hr_message_at = timezone.now()
        self.save()

    def accept_offer(self):
        """Employee stays — resignation is withdrawn."""
        self.status = 'WITHDRAWN'
        self.employee_reply = "Accepted HR's offer and withdrew the resignation."
        self.employee_replied_at = timezone.now()
        self.save()

    def quit_anyway(self, message=''):
        """Employee still wants to leave. Goes back to HR to allot a notice period."""
        self.status = 'PENDING'
        self.employee_reply = message or "I'd still like to proceed with my resignation."
        self.employee_replied_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Resignation - {self.user} ({self.status})"