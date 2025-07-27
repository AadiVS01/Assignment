from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import render

from .models import Product, StockTransaction
from .serializers import ProductSerializer, StockTransactionSerializer

# --- API Views ---

# FIX: Changed from ReadOnlyModelViewSet to ModelViewSet to allow POST requests
class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows products to be viewed or created.
    Provides a 'inventory' view to see the current stock levels of all products.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=False, methods=['get'], url_path='inventory')
    def inventory(self, request):
        """
        A custom action to get a snapshot of the current inventory levels.
        This is the primary endpoint for checking stock.
        """
        inventory_data = self.get_queryset().order_by('part_no')
        serializer = self.get_serializer(inventory_data, many=True)
        return Response(serializer.data)


class StockTransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows stock transactions to be viewed or created.
    Creating a transaction here will automatically update the stock levels
    of the associated products.
    """
    queryset = StockTransaction.objects.prefetch_related('details', 'details__product').all()
    serializer_class = StockTransactionSerializer

    def create(self, request, *args, **kwargs):
        """
        Override create to provide more specific error messages.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # The line below is technically redundant due to raise_exception=True, but good practice
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- UI View ---

def inventory_ui(request):
    """
    A simple Django view that renders the main HTML page.
    This page will contain the JavaScript to interact with our API.
    """
    return render(request, 'inventory/index.html')
