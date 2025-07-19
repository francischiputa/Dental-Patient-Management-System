
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from appointment import views as appointment_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('templates.urls')),
    path('create-appointment/', appointment_views.create_appointment, name='create_appointment'),
    path('clear-appointment-created-flag/', appointment_views.clear_appointment_created_flag, name='clear_appointment_created_flag'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)