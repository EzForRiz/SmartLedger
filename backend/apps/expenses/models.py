from django.db import models

class Expense(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('easypaisa', 'Easypaisa'),
        ('jazzcash', 'JazzCash'),
    ]

    CATEGORY_CHOICES = [
        ('Personal', 'Personal'),
        ('Professional', 'Professional'),
    ]

    amount = models.FloatField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)

    # ✅ FIXED (removed auto_now_add)
    date = models.DateField()

    time = models.TimeField(null=True, blank=True)
    where_spent = models.CharField(max_length=255)