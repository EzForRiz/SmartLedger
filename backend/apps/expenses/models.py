# apps/expenses/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(9999999)]
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    where_spent = models.CharField(max_length=255)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.date} | {self.category} | Rs {self.amount}"