from django import forms
from django.core.exceptions import ValidationError

from workouts import methods as workout_methods
from workouts.exceptions import FitFileException


class CreateWorkoutForm(forms.Form):
    name = forms.CharField(max_length=128, required=False)
    fit_file = forms.FileField()

    def clean_fit_file(self):
        try:
            workout_methods.validate_fit_file(self.cleaned_data["fit_file"])
            self.cleaned_data["fit_file"].seek(0)
        except FitFileException as e:
            raise ValidationError(e.message)

        return self.cleaned_data["fit_file"]
