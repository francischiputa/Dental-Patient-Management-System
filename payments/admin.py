from django.contrib import admin
from .models import Invoice, InvoiceService, Payment, Quotation, Receipt

admin.site.register(Invoice)
admin.site.register(InvoiceService)
admin.site.register(Payment)
admin.site.register(Quotation)
admin.site.register(Receipt)  # Assuming Receipt is defined in models.py

# Register your models here.
