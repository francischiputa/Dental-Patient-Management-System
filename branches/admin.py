from django.contrib import admin
from .models import Branch

# Register your models here.

admin.site.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'phone', 'email', 'created_at', 'updated_at')
    search_fields = ('name', 'location', 'phone', 'email')
    list_filter = ('created_at', 'updated_at')