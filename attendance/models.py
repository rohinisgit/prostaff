from datetime import datetime, time
from django.db import models
from django.conf import settings

SHIFT_START = time(9, 30)  # 9:30 AM shift start used for late detection


class AttendanceRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_late = models.BooleanField(default=False)
    late_minutes = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if self.in_time and self.out_time:
            delta = self.out_time - self.in_time
            self.total_hours = round(delta.total_seconds() / 3600, 2)
        if self.in_time:
            shift_start_dt = datetime.combine(self.date, SHIFT_START)
            in_time_naive = self.in_time.replace(tzinfo=None) if self.in_time.tzinfo else self.in_time
            if in_time_naive > shift_start_dt:
                self.is_late = True
                self.late_minutes = int((in_time_naive - shift_start_dt).total_seconds() / 60)
            else:
                self.is_late = False
                self.late_minutes = 0
        super().save(*args, **kwargs)

    @property
    def payroll_cycle_label(self):
        """Payroll cycle runs 26th (prev month) to 25th (this month)."""
        if self.date.day >= 26:
            start_month = self.date.month
        else:
            start_month = self.date.month - 1 or 12
        return f"Cycle starting {start_month}/26"

    def __str__(self):
        return f"{self.user} - {self.date}"
