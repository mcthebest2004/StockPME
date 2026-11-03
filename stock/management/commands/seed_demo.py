from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from stock.models import Enterprise, Article, Movement

class Command(BaseCommand):
    help = 'Crée une entreprise de démonstration locale (sans modifier un compte existant).'
    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo')
        parser.add_argument('--password', default='StockPME-demo-2026!')
    @transaction.atomic
    def handle(self, *args, **options):
        if User.objects.filter(username=options['username']).exists():
            raise CommandError('Ce compte existe déjà. Aucune donnée modifiée. Choisissez --username pour un autre compte.')
        user = User.objects.create_user(username=options['username'], password=options['password'])
        enterprise = Enterprise.objects.create(owner=user, name='Boutique Démo', currency='CDF')
        for name, category, price, quantity, alert in [
            ('Savon artisanal', 'Hygiène', '2500', 32, 5),
            ('Riz parfumé 1 kg', 'Alimentation', '4500', 48, 10),
            ('Huile végétale 1 L', 'Alimentation', '7000', 4, 5),
            ('Cahier 100 pages', 'Papeterie', '1500', 65, 10),
            ('Jus de mangue', 'Boissons', '3000', 0, 8),
            ('Gel désinfectant', 'Hygiène', '3500', 16, 5),
        ]:
            article = Article.objects.create(enterprise=enterprise, name=name, category=category, price=Decimal(price), quantity=quantity, alert=alert)
            Movement.objects.create(article=article, actor=user, kind='initial', delta=quantity, balance=quantity, unit_price=article.price, note='Données de démonstration')
        self.stdout.write(self.style.SUCCESS(f'Entreprise de démonstration créée. Identifiant : {user.username}'))
