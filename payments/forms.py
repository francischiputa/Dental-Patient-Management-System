# forms.py
from django import forms
from .models import Invoice, Payment
from appointment.models import Service

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['patient', 'appointment', 'services']

    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['patient', 'appointment', 'services']

    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']

    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice')
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        remaining = self.invoice.get_remaining_balance()
        if amount > remaining:
            raise forms.ValidationError(f"Amount cannot exceed remaining balance of {remaining:.2f}")
        return amount