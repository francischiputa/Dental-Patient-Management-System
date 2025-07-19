from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from branches.models import Branch
from .models import InventoryItem, InventoryTransaction, Supplier
from .forms import ItemForm, SupplierForm, TransactionForm
from django.contrib import messages

@login_required
def inventory_dashboard(request):
    low_stock_items = InventoryItem.objects.filter(quantity__lte=models.F('reorder_level'))
    recent_transactions = InventoryTransaction.objects.all().order_by('-timestamp')[:5]
    
    context = {
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions
    }
    return render(request, 'inventory/dashboard.html', context)

# List view
@login_required
def item_list(request):
    if request.user.user_type == 1:  # Admin
        items = InventoryItem.objects.all()
    else:
        items = InventoryItem.objects.filter(branch=request.user.branch)
    return render(request, 'inventory/item_list.html', {'items': items})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    transactions = item.transactions.all().order_by('-timestamp')[:10]
    return render(request, 'templates/item_detail.html', {
        'item': item,
        'transactions': transactions
    })
# Create view
@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            if request.user.user_type != 1:  # Not admin
                item.branch = request.user.branch
            item.save()
            return redirect('inventory:item_list')
    else:
        form = ItemForm()
    return render(request, 'inventory/form.html', {'form': form, 'title': 'Add New Item'})

# Update view
@login_required
def item_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.user.user_type != 1 and item.branch != request.user.branch:
        return HttpResponseForbidden("You do not have permission to edit this item.")
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{form.cleaned_data['name']}' updated successfully")
            return redirect('inventory:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)
    return render(request, 'inventory/form.html', {
        'form': form, 
        'item': item,
        'title': f'Edit {item.name}'
    })

# Delete view
@login_required
def item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.user.user_type != 1 and item.branch != request.user.branch:
        return HttpResponseForbidden("You do not have permission to delete this item.")
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"Item '{item_name}' has been deleted")
        return redirect('inventory:item_list')
    return render(request, 'inventory/item_confirm_delete.html', {
        'item': item,
        'title': f'Delete {item.name}'
    })

# Transaction view
@login_required
def item_transactions(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.user.user_type != 1 and item.branch != request.user.branch:
        return HttpResponseForbidden("You do not have permission to view transactions for this item.")
    transactions = item.transactions.all().order_by('-timestamp')
    return render(request, 'inventory/item_transactions.html', {
        'item': item,
        'transactions': transactions,
        'title': f'{item.name} - Transactions'
    })

# Add similar views for Supplier, Transaction, etc.