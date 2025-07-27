from rest_framework import serializers
from .models import Product, StockTransaction, StockTransactionDetail
from django.db import transaction

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model. Includes current stock.
    """
    class Meta:
        model = Product
        fields = ['id', 'part_no', 'description', 'current_stock']


class StockTransactionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for line items within a transaction.
    Used for read operations and as a nested serializer.
    """
    # To show product part_no instead of just the ID
    product_part_no = serializers.CharField(source='product.part_no', read_only=True)

    class Meta:
        model = StockTransactionDetail
        fields = ['id', 'product', 'product_part_no', 'quantity']
        read_only_fields = ['id', 'product_part_no']


class StockTransactionSerializer(serializers.ModelSerializer):
    """
    Main serializer for creating and viewing stock transactions.
    Handles nested creation of transaction details.
    """
    details = StockTransactionDetailSerializer(many=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = StockTransaction
        fields = ['id', 'transaction_code', 'transaction_type', 'transaction_type_display', 'date', 'notes', 'details']
        read_only_fields = ['id', 'date', 'transaction_type_display']

    def create(self, validated_data):
        """
        Handle creation of the transaction and its nested detail lines
        within a single database transaction for data integrity.
        """
        details_data = validated_data.pop('details')
        
        if not details_data:
            raise serializers.ValidationError("A transaction must have at least one detail line.")

        try:
            with transaction.atomic():
                # Create the main transaction record
                stock_transaction = StockTransaction.objects.create(**validated_data)
                
                # Create each detail line, which will trigger the stock update logic in the model's save() method
                for detail_data in details_data:
                    # The model's save method will handle stock validation and updates
                    StockTransactionDetail.objects.create(transaction=stock_transaction, **detail_data)

        except Exception as e:
            # Catch exceptions from the model layer (e.g., insufficient stock) and raise a DRF validation error
            raise serializers.ValidationError(str(e))
            
        return stock_transaction

