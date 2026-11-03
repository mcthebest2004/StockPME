from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

MAX_QUANTITY = 2147483647

def photo_path(instance, filename):
    return f'articles/{uuid4().hex}{Path(filename).suffix.lower()}'

class Enterprise(models.Model):
    CURRENCIES = [('CDF', 'Franc congolais (CDF)'), ('USD', 'Dollar américain (USD)'), ('EUR', 'Euro (EUR)'), ('XOF', 'Franc CFA (XOF)')]
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enterprise')
    name = models.CharField('Nom de l’entreprise', max_length=120)
    currency = models.CharField('Devise', max_length=3, choices=CURRENCIES, default='CDF')
    def __str__(self):
        return self.name

class Article(models.Model):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE)
    name = models.CharField('Nom de l’article', max_length=160)
    category = models.CharField('Catégorie', max_length=80, blank=True)
    price = models.DecimalField('Prix de vente unitaire', max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField('Quantité initiale', default=0, validators=[MaxValueValidator(MAX_QUANTITY)])
    alert = models.PositiveIntegerField('Seuil d’alerte', default=5, validators=[MaxValueValidator(MAX_QUANTITY)])
    photo = models.ImageField('Photo (JPEG, PNG ou WebP, 5 Mo maximum)', upload_to=photo_path, blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name='article_price_nonnegative')]
    @property
    def low(self):
        return self.quantity <= self.alert
    def __str__(self):
        return self.name

class Movement(models.Model):
    KINDS = [('initial', 'Stock initial'), ('in', 'Entrée / réapprovisionnement'), ('sale', 'Vente'), ('out', 'Sortie / perte')]
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name='movements')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField('Type', max_length=10, choices=KINDS)
    delta = models.IntegerField('Variation')
    balance = models.PositiveIntegerField('Stock après mouvement')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField('Référence / commentaire', max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-pk']
