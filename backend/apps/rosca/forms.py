import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Participant, ROSCAGroup


def format_cnic(value):
    """Strip non-digits and return XXXXX-XXXXXXX-X, or raise ValidationError."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 13:
        raise ValidationError("CNIC must be exactly 13 digits.")
    if not digits.isdigit():
        raise ValidationError("CNIC must contain numbers only.")
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"


class ROSCARegistrationForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=ROSCAGroup.objects.filter(is_active=True),
        empty_label="— Select a committee pool —",
        label="ROSCA Pool",
    )

    class Meta:
        model = Participant
        fields = ["full_name", "phone_number", "cnic", "group"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full name as on CNIC"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "03001234567"}),
            "cnic": forms.TextInput(
                attrs={
                    "placeholder": "3520112345671",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                    "maxlength": "15",
                    "class": "rosca-input cnic-auto-format",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "rosca-input")

    def clean_cnic(self):
        return format_cnic(self.cleaned_data["cnic"])

    def clean_group(self):
        group = self.cleaned_data["group"]
        if self.user and Participant.objects.filter(user=self.user, group=group).exists():
            raise forms.ValidationError("You are already registered in this pool.")
        return group

    def save(self, commit=True):
        participant = super().save(commit=False)
        participant.user = self.user
        if commit:
            participant.save()
        return participant
