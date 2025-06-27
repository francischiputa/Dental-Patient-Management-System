from django.db import models
from patient.models import Patient
from user_accounts.models import Dentist  # Correctly import the Dentist model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from user_accounts.models import CustomUser
from branches.models import Branch  # Import the Branch model



class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, blank=True, null=True)
    date_time = models.DateTimeField()
    status_choices = [('Pending', 'Pending'), ('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')]
    status = models.CharField(max_length=20, choices=status_choices, default='Pending')
    notes = models.TextField(blank=True, null=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_patient_new = models.BooleanField(default=False)
    branch = models.ForeignKey(Branch,blank=True, null=True, on_delete=models.CASCADE)  # Link to branch

    def __str__(self):
        return f"Appointment for {self.patient} with {self.dentist.user.username} on {self.date_time}"

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    duration = models.DurationField(blank=True, null=True)
    branch = models.ForeignKey(Branch, blank=True, null=True, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.price is None:
            raise ValueError("Price cannot be None.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Diagnosis(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, blank=True, null=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, blank=True, null=True)
    diagnosis_text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, blank=True, null=True, on_delete=models.CASCADE)  # Link to branch

    def __str__(self):
        return f"Diagnosis for {self.appointment.patient} on {self.date}"

class Treatment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, blank=True, null=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, blank=True, null=True)
    treatment_text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, blank=True, null=True, on_delete=models.CASCADE)  # Link to branch

    def __str__(self):
        return f"Treatment for {self.appointment.patient} on {self.date}"