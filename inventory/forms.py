from django import forms
from .models import InventoryItem, Supplier, InventoryTransaction, ItemCategory

class ItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = '__all__'

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

class TransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['transaction_type', 'quantity', 'reference']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'description']  # Include the fields you want in the form