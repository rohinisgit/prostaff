from django import forms
from core.models import User
from increments.models import IncrementFeedback

DECIMAL_ONINPUT = (
    "this.value = this.value.replace(/[^0-9.]/g, '')"
    ".replace(/(\\..*)\\./g, '$1')"
)


class IncrementRequestForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Employee")
    feedback_manager = forms.ModelChoiceField(
        queryset=User.objects.filter(role='MANAGER'), required=False,
        label="Manager (for Feedback)"
    )
    requested_basic = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT})
    )
    effective_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        acting_user = kwargs.pop('acting_user', None)
        super().__init__(*args, **kwargs)
        qs = User.objects.all()
        if acting_user:
            qs = qs.exclude(id=acting_user.id)
        self.fields['user'].queryset = qs
        self.fields['feedback_manager'].queryset = User.objects.filter(role='MANAGER')
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned = super().clean()
        emp_user = cleaned.get('user')
        feedback_manager = cleaned.get('feedback_manager')
        # Only require a manager pick when the increment target is a plain
        # Employee. Managers and Admins never need feedback.
        if emp_user and emp_user.role == 'EMPLOYEE' and not feedback_manager:
            self.add_error('feedback_manager', "Select a manager to send this employee's increment to for feedback.")
        return cleaned


class IncrementFeedbackForm(forms.ModelForm):
    class Meta:
        model = IncrementFeedback
        fields = ['suggestion', 'description']
        widgets = {
            'suggestion': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'rows': 3, 'class': 'form-control',
                'placeholder': "Tell HR why you feel this way about this employee's performance...",
            }),
        }