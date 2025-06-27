from django.contrib.auth.models import AbstractUser
from django.db import models
from branches.models import Branch  # Import the Branch model


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'admin'),
        (2, 'dentist'),
        (3, 'staff'),
    )
    user_type = models.PositiveSmallIntegerField(
        choices=USER_TYPE_CHOICES,
        default=1  # Default to 'admin'
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    
class Dentist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    available_days = models.JSONField(default=list)  # Store days as a list (e.g., ["Monday", "Wednesday"])

    @property
    def branch(self):
        return self.user.branch

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} ({self.specialization})"
    

class Staff(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 3}  # Ensure only staff users can be linked
    )
    role = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)

    @property
    def branch(self):
        return self.user.branch  # Access the branch through the user

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.role}"