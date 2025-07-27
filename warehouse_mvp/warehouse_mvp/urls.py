from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line tells Django to look at the 'inventory.urls' file
    # for any URL that isn't '/admin/'.
    path('', include('inventory.urls')),
]

