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
    notes = forms.CharField(
        widget=forms.Textarea,
        required=False,
        initial="Default notes"
    )

    class Meta:
        model = InventoryTransaction
        fields = ['item', 'transaction_type', 'quantity', 'timestamp']  # Exclude 'notes' from the model fields

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item', None)
        super(TransactionForm, self).__init__(*args, **kwargs)

        # Set the initial value for the notes field
        if self.item:
            self.fields['notes'].initial = f"Transaction for {self.item.name}"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'description']  # Include the fields you want in the form