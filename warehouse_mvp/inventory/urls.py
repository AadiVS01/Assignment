from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Notice the dot '.' before views. This means "import from the current directory".
from .views import ProductViewSet, StockTransactionViewSet, inventory_ui

# Create a router for our API viewsets.
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'transactions', StockTransactionViewSet, basename='stocktransaction')

# The API URLs are now determined automatically by the router.
# The UI view is a separate path.
urlpatterns = [
    # All API endpoints will be under /api/ (e.g., /api/products/, /api/transactions/)
    path('api/', include(router.urls)),
    
    # The root path of the site ('/') will serve our main HTML page.
    path('', inventory_ui, name='inventory-ui'),
]
