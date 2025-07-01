from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # path('', views.inventory_dashboard, name='dashboard'),
    path('items/', views.item_list, name='item_list'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('items/new/', views.item_create, name='item_create'),
    # Add paths for suppliers, transactions, etc.
]