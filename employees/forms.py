from django import forms
from core.validators import (
    name_validator, phone_validator, alnum_id_validator,
    bank_account_validator, ifsc_validator, pan_validator, aadhar_validator,
    COUNTRY_CODES,
)
from employees.models import EmployeeProfile, EmployeeDocument, ResignationRequest
from core.models import User

NAME_ATTRS = {
    'pattern': "[A-Za-z0-9' -]*", 'title': "Letters, numbers, spaces, hyphens and apostrophes only.",
    'maxlength': 150, 'oninput': "this.value = this.value.replace(/[^A-Za-z0-9' -]/g, '')",
}
PHONE_ATTRS = {
    'inputmode': 'numeric', 'pattern': '[0-9]{10}', 'title': "Enter exactly 10 digits.",
    'maxlength': 10, 'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10)",
}
COUNTRY_CODE_ATTRS = {'class': 'form-control', 'style': 'max-width:150px; flex-shrink:0;'}
ID_ATTRS = {
    'pattern': '[A-Za-z0-9-]*', 'title': "Letters, numbers and hyphens only.",
    'maxlength': 20, 'oninput': "this.value = this.value.replace(/[^A-Za-z0-9-]/g, '')",
}
BANK_ATTRS = {
    'inputmode': 'numeric', 'pattern': '[0-9]{9,18}', 'title': "9 to 18 digits only.",
    'maxlength': 18, 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
}
IFSC_ATTRS = {
    'pattern': '[A-Za-z]{4}0[A-Za-z0-9]{6}', 'title': "Format: 4 letters + 0 + 6 alphanumeric (e.g. HDFC0001234).",
    'maxlength': 11, 'style': 'text-transform:uppercase;',
    'oninput': "this.value = this.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase()",
}
PAN_ATTRS = {
    'pattern': '[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}', 'title': "Format: 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F).",
    'maxlength': 10, 'style': 'text-transform:uppercase;',
    'oninput': "this.value = this.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase()",
}
AADHAR_ATTRS = {
    'inputmode': 'numeric', 'pattern': '[0-9]{12}', 'title': "Exactly 12 digits.",
    'maxlength': 12, 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
}


class EmployeeSelfEditForm(forms.ModelForm):
    """Fields an employee is allowed to edit on their own profile."""
    first_name = forms.CharField(max_length=150, required=False, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    last_name = forms.CharField(max_length=150, required=False, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    phone_country_code = forms.ChoiceField(choices=COUNTRY_CODES, required=False, widget=forms.Select(attrs=COUNTRY_CODE_ATTRS))
    phone = forms.CharField(max_length=10, required=False, validators=[phone_validator], widget=forms.TextInput(attrs=PHONE_ATTRS))

    class Meta:
        model = EmployeeProfile
        fields = [
            'address', 'bank_account', 'ifsc_code', 'pan_no', 'aadhar_no',
            'emergency_contact_name', 'emergency_contact_country_code', 'emergency_contact_phone',
            'profile_photo',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'bank_account': forms.TextInput(attrs=BANK_ATTRS),
            'ifsc_code': forms.TextInput(attrs=IFSC_ATTRS),
            'pan_no': forms.TextInput(attrs=PAN_ATTRS),
            'aadhar_no': forms.TextInput(attrs=AADHAR_ATTRS),
            'emergency_contact_name': forms.TextInput(attrs=NAME_ATTRS),
            'emergency_contact_country_code': forms.Select(attrs=COUNTRY_CODE_ATTRS),
            'emergency_contact_phone': forms.TextInput(attrs=PHONE_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        for name in ['bank_account', 'ifsc_code', 'pan_no', 'aadhar_no', 'emergency_contact_name', 'emergency_contact_phone']:
            self.fields[name].required = False
        self.fields['bank_account'].validators.append(bank_account_validator)
        self.fields['ifsc_code'].validators.append(ifsc_validator)
        self.fields['pan_no'].validators.append(pan_validator)
        self.fields['aadhar_no'].validators.append(aadhar_validator)
        self.fields['emergency_contact_name'].validators.append(name_validator)
        self.fields['emergency_contact_phone'].validators.append(phone_validator)
        if self.user_instance:
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['phone'].initial = self.user_instance.phone
            self.fields['phone_country_code'].initial = self.user_instance.phone_country_code

    def clean_ifsc_code(self):
        return self.cleaned_data.get('ifsc_code', '').upper()

    def clean_pan_no(self):
        return self.cleaned_data.get('pan_no', '').upper()

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if self.user_instance:
            self.user_instance.first_name = self.cleaned_data.get('first_name', '')
            self.user_instance.last_name = self.cleaned_data.get('last_name', '')
            self.user_instance.phone = self.cleaned_data.get('phone', '')
            self.user_instance.phone_country_code = self.cleaned_data.get('phone_country_code') or '+91'
            if commit:
                self.user_instance.save()
        return profile


class NewEmployeeForm(forms.ModelForm):
    """Used by HR to onboard a new employee (creates the User).
    Employee ID is no longer collected here — HR assigns it later from the
    employee's Edit Profile page if needed."""
    password = forms.CharField(widget=forms.PasswordInput, help_text="Temporary password for the employee")
    first_name = forms.CharField(max_length=150, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    last_name = forms.CharField(max_length=150, required=False, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    phone_country_code = forms.ChoiceField(choices=COUNTRY_CODES, required=False, widget=forms.Select(attrs=COUNTRY_CODE_ATTRS))
    phone = forms.CharField(max_length=10, required=False, validators=[phone_validator], widget=forms.TextInput(attrs=PHONE_ATTRS))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'role', 'department', 'date_joined_company', 'phone_country_code', 'phone', 'password']
        widgets = {'date_joined_company': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        department = self.cleaned_data.get('department')
        if department and department.manager_id and user.role != User.ROLE_MANAGER:
            user.manager = department.manager
        else:
            user.manager = None
        if commit:
            user.save()
        return user


class HREmployeeEditForm(forms.ModelForm):
    """HR edits an employee's core profile details from the directory's
    Edit button — name, contact info, department, employee ID, joining date."""
    first_name = forms.CharField(max_length=150, required=False, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    last_name = forms.CharField(max_length=150, required=False, validators=[name_validator], widget=forms.TextInput(attrs=NAME_ATTRS))
    phone_country_code = forms.ChoiceField(choices=COUNTRY_CODES, required=False, widget=forms.Select(attrs=COUNTRY_CODE_ATTRS))
    phone = forms.CharField(max_length=10, required=False, validators=[phone_validator], widget=forms.TextInput(attrs=PHONE_ATTRS))
    employee_id = forms.CharField(max_length=20, required=False, validators=[alnum_id_validator], widget=forms.TextInput(attrs=ID_ATTRS))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'employee_id', 'department', 'date_joined_company', 'phone_country_code', 'phone']
        widgets = {'date_joined_company': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class HRDocumentForm(forms.ModelForm):
    """HR can only upload official, company-issued letters — never an
    employee's personal documents."""
    doc_type = forms.ChoiceField(
        choices=[c for c in EmployeeDocument.DOC_TYPES if c[0] in EmployeeDocument.HR_DOC_TYPES],
        label="Document Type",
    )

    class Meta:
        model = EmployeeDocument
        fields = ['doc_type', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class SelfDocumentForm(forms.ModelForm):
    """Everyone uploads their own personal documents here."""
    doc_type = forms.ChoiceField(
        choices=[c for c in EmployeeDocument.DOC_TYPES if c[0] in EmployeeDocument.SELF_DOC_TYPES],
        label="Document Type",
    )

    class Meta:
        model = EmployeeDocument
        fields = ['doc_type', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class RoleChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role']

    def __init__(self, *args, **kwargs):
        acting_user = kwargs.pop('acting_user', None)
        super().__init__(*args, **kwargs)
        self.fields['role'].widget.attrs.setdefault('class', 'form-control')
        if acting_user and acting_user.role == 'HR':
            self.fields['role'].choices = [
                (User.ROLE_EMPLOYEE, 'Employee'),
                (User.ROLE_MANAGER, 'Manager'),
            ]


class ResignationRequestForm(forms.ModelForm):
    class Meta:
        model = ResignationRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Tell HR why you are resigning...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')