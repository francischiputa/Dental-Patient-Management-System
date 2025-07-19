from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from branches.models import Branch

class Supplier(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class ItemCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Item categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    category = models.ForeignKey(
        ItemCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='items'
    )
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    available_stock = models.IntegerField(default=0) 
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='supplied_items'
    )
    last_updated = models.DateTimeField(auto_now=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='inventory_items'
    )
    test_field = models.BooleanField(default=False)  # Dummy field for migration test

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def __str__(self):
        return f"{self.name} ({self.quantity} in stock)"

    def save(self, *args, **kwargs):
        """Ensure reorder level doesn't exceed max allowed value"""
        if self.reorder_level > self.quantity:
            self.reorder_level = min(self.quantity, 10)  # Default fallback
        super().save(*args, **kwargs)


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUST', 'Adjustment'),
    )
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)

    # def clean(self):
    #     if not self.item_id:
    #         raise ValidationError("An item must be selected for the transaction.")
        
    #     if self.transaction_type == 'OUT' and self.quantity > self.item.stock:
    #         raise ValidationError("Cannot remove more items than available in stock.")