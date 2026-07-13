from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from payroll.models import SalaryStructure

# Numeric-only handler: allows digits and a single decimal point as the
# user types, stripping anything else (letters, symbols, extra dots).
DECIMAL_ONINPUT = (
    "this.value = this.value.replace(/[^0-9.]/g, '')"
    ".replace(/(\\..*)\\./g, '$1')"
)


class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = ['basic', 'hra', 'other_allowances', 'bonus', 'pf_applicable', 'pf_percent']
        widgets = {
            'basic': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT}),
            'hra': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT}),
            'other_allowances': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT}),
            'bonus': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT}),
            'pf_percent': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100', 'inputmode': 'decimal', 'oninput': DECIMAL_ONINPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'pf_applicable':
                field.widget.attrs.setdefault('class', 'form-control')
        self.fields['basic'].validators.append(MinValueValidator(0))
        self.fields['hra'].validators.append(MinValueValidator(0))
        self.fields['other_allowances'].validators.append(MinValueValidator(0))
        self.fields['bonus'].validators.append(MinValueValidator(0))
        self.fields['pf_percent'].validators.append(MinValueValidator(0))
        self.fields['pf_percent'].validators.append(MaxValueValidator(100))