from django import forms
from core.models import User
from queries.models import EmployeeQuery, QueryMessage


class EmployeeQueryForm(forms.ModelForm):
    recipient_role = forms.ChoiceField(choices=EmployeeQuery.RECIPIENT_CHOICES, label="Send To (Role)")
    recipient_user = forms.ModelChoiceField(queryset=User.objects.none(), label="Send To (Person)")

    class Meta:
        model = EmployeeQuery
        fields = ['recipient_role', 'recipient_user', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Type your query here...'}),
        }

    def __init__(self, *args, **kwargs):
        self.acting_user = kwargs.pop('acting_user', None)
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(role__in=['ADMIN', 'HR', 'MANAGER'])
        if self.acting_user:
            qs = qs.exclude(id=self.acting_user.id)
        self.fields['recipient_user'].queryset = qs
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('recipient_role')
        recipient_user = cleaned.get('recipient_user')
        if role and recipient_user and recipient_user.role != role:
            self.add_error('recipient_user', "Selected person doesn't match the chosen role.")
        return cleaned


class QueryMessageForm(forms.ModelForm):
    class Meta:
        model = QueryMessage
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type a reply...', 'class': 'form-control'}),
        }