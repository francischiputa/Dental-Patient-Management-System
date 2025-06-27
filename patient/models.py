from django.db import models
from branches.models import Branch  # Import the Branch model

class Patient(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(blank=True, null=True)
    gender_choices = [('M', 'Male'), ('F', 'Female')]
    gender = models.CharField(max_length=1, choices=gender_choices, blank=True, null=True)
    nrc = models.CharField(max_length=55, blank=True, null=True)  # National Registration Card number
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    medical_history = models.TextField(blank=True, null=True)
    branch = models.ForeignKey(
        Branch,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='patients'  # Allows querying patients by branch
    )
    is_patient = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Returns the full name of the patient."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Calculates the age of the patient based on their date of birth."""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
            return age
        return None