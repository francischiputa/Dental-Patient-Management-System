from django.db import models
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models import Sum
from patient.models import Patient
from appointment.models import Appointment, Service
import uuid
from branches.models import Branch  # Import the Branch model
from dentist.models import CustomUser as User
from django.db import IntegrityError

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid')
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    services = models.ManyToManyField(Service, through='InvoiceService')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) 
    notes = models.TextField(blank=True, null=True)
    branch = models.ForeignKey(
        Branch,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='invoices'  # Allows querying invoices by branch
    )

    def get_total_payments(self):
        return self.payment_set.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    
    def calculate_total(self):
        return self.invoiceservice_set.aggregate(
            total=models.Sum(models.F('price_at_time') * models.F('quantity'))
        )['total'] or Decimal('0.00')

    def update_total_amount(self):
        self.total_amount = self.calculate_total()
        self.save()

    def get_remaining_balance(self):
        total_payments = self.payment_set.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        return self.total_amount - total_payments

    def __str__(self):
        return f"Invoice #{self.id} for {self.patient}"

class InvoiceService(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.update_total_amount()

    def __str__(self):
        return f"{self.service.name} x {self.quantity} @ {self.price_at_time}"

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mobile', 'Mobile Payment'),
        ('bank', 'Bank Transfer')
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('ongoing', 'Ongoing')
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)  # For mobile/bank payments
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    branch = models.ForeignKey(
        Branch,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='payments'  # Allows querying payments by branch
    )

    def get_existing_receipt(self):
        return Receipt.objects.filter(payment__invoice=self.invoice).first()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_invoice_status()

    def update_invoice_status(self):
        total_paid = Payment.objects.filter(
            invoice=self.invoice,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        if total_paid >= self.invoice.total_amount:
            self.invoice.status = 'paid'
        elif total_paid > 0:
            self.invoice.status = 'partial'
        else:
            self.invoice.status = 'issued'
        self.invoice.save()

    def __str__(self):
        return f"{self.patient} - {self.amount}"


class Receipt(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The invoice associated with this receipt."
    )
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.CASCADE)
    
    items = models.ManyToManyField(
        'inventory.InventoryItem',
        through='ReceiptItem',
        help_text="Items included in this receipt."
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        help_text="The patient associated with this receipt."
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        help_text="The branch where this receipt was issued."
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Unique identifier for the receipt."
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the receipt was issued."
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The service associated with this receipt."
    )
    quantity = models.PositiveIntegerField(
        default=1,
        blank=True,
        null=True,
        help_text="Quantity of the service or item."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price of the item or service at the time of receipt creation."
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total amount of the receipt."
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for the receipt."
    )

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            for _ in range(5):  # Try up to 5 times to avoid a collision
                candidate = f"RECEIPT-{uuid.uuid4().hex[:8]}"
                if not Receipt.objects.filter(receipt_number=candidate).exists():
                    self.receipt_number = candidate
                    break
            else:
                raise ValueError("Could not generate a unique receipt number after 5 attempts.")
        super().save(*args, **kwargs)

class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.CASCADE)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price of the item at the time of receipt creation."
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    services = models.ManyToManyField(Service, through='QuotationService')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    valid_until = models.DateField(null=True, blank=True)  # Optional field
    branch = models.ForeignKey(
        Branch,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='quotations'  # Allows querying quotations by branch
    )
    
    def calculate_total(self):
        return self.quotationservice_set.aggregate(
            total=models.Sum(models.F('price_at_time') * models.F('quantity'))
        )['total'] or Decimal('0.00')

    def save(self, *args, **kwargs):
        # Calculate the total amount only if the instance already exists
        if self.pk:  # Check if the instance has been saved before
            self.total_amount = self.calculate_total()
        
        # Save the instance (this will generate the primary key if it doesn't exist)
        super().save(*args, **kwargs)

class QuotationService(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service.name} x {self.quantity} @ {self.price_at_time}"