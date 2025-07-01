from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import InventoryItem, InventoryTransaction, Supplier
from .forms import ItemForm, SupplierForm, TransactionForm

@login_required
def inventory_dashboard(request):
    low_stock_items = InventoryItem.objects.filter(quantity__lte=models.F('reorder_level'))
    recent_transactions = InventoryTransaction.objects.all().order_by('-timestamp')[:5]
    
    context = {
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def item_list(request):
    items = InventoryItem.objects.all()
    return render(request, 'inventory/item_list.html', {'items': items})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    transactions = item.transactions.all().order_by('-timestamp')[:10]
    return render(request, 'templates/item_detail.html', {
        'item': item,
        'transactions': transactions
    })
@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:item_list')
    else:
        form = ItemForm()
    return render(request, 'inventory/form.html', {'form': form, 'title': 'Add New Item'})

# Add similar views for Supplier, Transaction, etc.