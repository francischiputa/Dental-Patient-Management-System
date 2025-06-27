from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Staff, Dentist
from branches.models import Branch

# Custom Admin for CustomUser
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'branch')  # Include 'branch' in the list display
    list_filter = ('user_type', 'branch')  # Add 'branch' to filters
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Branch Info', {'fields': ('branch', 'user_type')}),  # Add 'branch' and 'user_type' to the fieldsets
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'user_type', 'branch'),  # Include 'branch' here
        }),
    )

# Register the CustomUser model with the custom admin class
admin.site.register(CustomUser, CustomUserAdmin)

# Custom Admin for Dentist
class DentistAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'contact_number', 'branch')  # Include 'branch'
    list_filter = ('user__branch',)  # Reference the branch through the user field
    readonly_fields = ('branch',)  # Make 'branch' read-only since it's managed via CustomUser

    def branch(self, obj):
        return obj.user.branch  # Access the branch through the related CustomUser

    branch.short_description = 'Branch'  # Optional: Set a human-readable name for the column

admin.site.register(Dentist, DentistAdmin)

# Custom Admin for Staff
class StaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'contact_number', 'branch')  # Include 'branch'
    list_filter = ('user__branch',)  # Reference the branch through the user field
    readonly_fields = ('branch',)  # Make 'branch' read-only since it's managed via CustomUser

    def branch(self, obj):
        return obj.user.branch  # Access the branch through the related CustomUser

    branch.short_description = 'Branch'  # Optional: Set a human-readable name for the column

admin.site.register(Staff, StaffAdmin)