from django.db import models

class Expense(models.Model):
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    amount = models.FloatField()
    where_spent = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=100)
    use_type = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.where_spent} - {self.amount}"