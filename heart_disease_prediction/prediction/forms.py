from django import forms
from .models import HealthCheck, DailyCheck

class PDFUploadForm(forms.Form):
    report = forms.FileField(label="Upload your medical report (PDF)")


class HealthCheckForm(forms.ModelForm):
    class Meta:
        model = HealthCheck
        fields = ['bp', 'cholesterol', 'sugar_level']
        widgets = {
            'bp': forms.TextInput(attrs={'class': 'form-control'}),
            'cholesterol': forms.TextInput(attrs={'class': 'form-control'}),
            'sugar_level': forms.TextInput(attrs={'class': 'form-control'}),
            
        }



class DailyCheckForm(forms.ModelForm):
    class Meta:
        model = DailyCheck
        fields = ['heart_rate', 'spo2', 'exercise_minutes']
        widgets = {
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'spo2': forms.NumberInput(attrs={'class': 'form-control'}),
            'exercise_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }
