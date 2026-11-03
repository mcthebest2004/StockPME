from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from .models import Article, Movement, MAX_QUANTITY

@transaction.atomic
def record_movement(*, article_id, enterprise, actor, kind, quantity, note=''):
    if kind not in {'in', 'out', 'sale'} or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
        raise ValidationError('Mouvement invalide.')
    delta = quantity if kind == 'in' else -quantity
    rows = Article.objects.filter(pk=article_id, enterprise=enterprise, archived=False)
    if delta < 0:
        rows = rows.filter(quantity__gte=quantity)
    else:
        rows = rows.filter(quantity__lte=MAX_QUANTITY - quantity)
    if rows.update(quantity=F('quantity') + delta) != 1:
        raise ValidationError('Stock insuffisant, quantité trop élevée ou article archivé. Rechargez la page et vérifiez la quantité.')
    article = Article.objects.get(pk=article_id, enterprise=enterprise)
    return Movement.objects.create(article=article, actor=actor, kind=kind, delta=delta, balance=article.quantity, unit_price=article.price, note=note)
