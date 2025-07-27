
# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# table prodmast - stores the details of the products
class Product(models.Model):
    """
    Represents a product in the warehouse (prodmast).
    """
    part_no = models.CharField(max_length=50, unique=True, help_text="Unique part number for the product.")
    description = models.TextField(blank=True, help_text="A brief description of the product.")
    # We add a calculated field for current stock level for simplicity.
    # In a high-performance system, this might be calculated on-the-fly.
    current_stock = models.IntegerField(default=0, help_text="The current available stock for this product.")

    def __str__(self):
        return f"{self.part_no} ({self.description[:30]})"

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['part_no']

# table stckmain - stores the transaction details
class StockTransaction(models.Model):
    """
    Represents a single stock transaction header (stckmain).
    This could be a goods receipt, a dispatch, or a stock adjustment.
    """
    TRANSACTION_TYPES = (
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    )
    transaction_code = models.CharField(max_length=20, unique=True, help_text="A unique code for the transaction (e.g., GRN-001, DO-001).")
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES, help_text="The type of transaction (IN or OUT).")
    date = models.DateTimeField(default=timezone.now, help_text="The date and time of the transaction.")
    notes = models.TextField(blank=True, null=True, help_text="Any notes related to the transaction.")

    def __str__(self):
        return f"{self.transaction_code} ({self.get_transaction_type_display()}) on {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Stock Transaction"
        verbose_name_plural = "Stock Transactions"
        ordering = ['-date']


# table stckdetail - stores the details of the products within each transaction
class StockTransactionDetail(models.Model):
    """
    Represents a line item within a stock transaction (stckdetail).
    Links a product and quantity to a main transaction.
    """
    transaction = models.ForeignKey(StockTransaction, related_name='details', on_delete=models.CASCADE, help_text="The parent transaction for this detail line.")
    product = models.ForeignKey(Product, related_name='stock_movements', on_delete=models.PROTECT, help_text="The product involved in this transaction line.")
    quantity = models.PositiveIntegerField(help_text="The quantity of the product for this transaction line.")

    def __str__(self):
        return f"{self.product.part_no} - Qty: {self.quantity}"

    def clean(self):
        """
        Validation logic before saving.
        """
        super().clean()
        if self.quantity <= 0:
            raise ValidationError("Quantity must be a positive number.")

    def save(self, *args, **kwargs):
        """
        Overrides the save method to update the product's current stock.
        This is a crucial piece of business logic.
        """
        self.full_clean() # Run validation

        # Use a database transaction to ensure atomicity
        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            # If the object is already in the DB, we need to revert the old stock change before applying the new one.
            if self.pk:
                old_instance = StockTransactionDetail.objects.get(pk=self.pk)
                if old_instance.transaction.transaction_type == 'IN':
                    old_instance.product.current_stock -= old_instance.quantity
                else: # OUT
                    old_instance.product.current_stock += old_instance.quantity
                old_instance.product.save()

            # Apply the new stock change
            if self.transaction.transaction_type == 'IN':
                self.product.current_stock += self.quantity
            elif self.transaction.transaction_type == 'OUT':
                # Check for sufficient stock before allowing an OUT transaction
                if self.product.current_stock < self.quantity:
                    raise ValidationError(f"Insufficient stock for {self.product.part_no}. Available: {self.product.current_stock}, Required: {self.quantity}")
                self.product.current_stock -= self.quantity

            self.product.save()
            super().save(*args, **kwargs) # Save the detail line itself

    def delete(self, *args, **kwargs):
        """
        Overrides the delete method to revert the stock change.
        """
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            if self.transaction.transaction_type == 'IN':
                self.product.current_stock -= self.quantity
            else: # OUT
                self.product.current_stock += self.quantity
            self.product.save()
            super().delete(*args, **kwargs)


    class Meta:
        verbose_name = "Stock Transaction Detail"
        verbose_name_plural = "Stock Transaction Details"
        # Ensure a product appears only once per transaction
        unique_together = ('transaction', 'product')
