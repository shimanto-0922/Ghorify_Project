from django.db import models

from accounts.models import User
from properties.models import Property


class Favourite(models.Model):
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favourites'
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='favourited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.tenant} likes {self.property}'


class Comparison(models.Model):
    # 2 or 3 favourite homes shown side by side
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comparisons'
    )
    name = models.CharField(max_length=80, default='My comparison')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.tenant})'


class ComparisonItem(models.Model):
    comparison = models.ForeignKey(
        Comparison,
        on_delete=models.CASCADE,
        related_name='items'
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='comparison_items'
    )
    position = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f'{self.property} in {self.comparison}'
