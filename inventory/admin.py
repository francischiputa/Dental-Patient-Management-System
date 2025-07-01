from django.contrib import admin
from .models import *

admin.site.register(Supplier)
admin.site.register(ItemCategory)
admin.site.register(InventoryItem)
admin.site.register(InventoryTransaction)