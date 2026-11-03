import csv
import io
import tempfile
from decimal import Decimal
from unittest.mock import patch
from PIL import Image
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import Article, Enterprise, Movement, MAX_QUANTITY
from .services import record_movement

class StockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('alice', password='Test-stock-2026!')
        cls.other = User.objects.create_user('bob', password='Test-stock-2026!')
        cls.company = Enterprise.objects.create(owner=cls.owner, name='Boutique Alice', currency='CDF')
        cls.other_company = Enterprise.objects.create(owner=cls.other, name='Boutique Bob', currency='USD')
        cls.article = Article.objects.create(enterprise=cls.company, name='Savon', category='Hygiène', quantity=10, price=Decimal('2.50'), alert=3)
        cls.private = Article.objects.create(enterprise=cls.other_company, name='Article secret', quantity=100, price=99)

    def setUp(self):
        self.client.force_login(self.owner)

    def move(self, kind='sale', quantity=3):
        return record_movement(article_id=self.article.pk, enterprise=self.company, actor=self.owner, kind=kind, quantity=quantity, note='V-001')

    def test_authentication_required(self):
        self.client.logout()
        for url in ['/', '/historique/', '/export/', '/articles/nouveau/', f'/articles/{self.article.pk}/photo/']:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_signup_creates_company_and_session(self):
        self.client.logout()
        response = self.client.post(reverse('signup'), {'username': 'claire', 'company_name': 'Chez Claire', 'currency': 'EUR', 'password1': 'Mon-stock-8672!', 'password2': 'Mon-stock-8672!'})
        self.assertRedirects(response, '/')
        self.assertEqual(Enterprise.objects.get(owner__username='claire').name, 'Chez Claire')

    def test_login_logout(self):
        self.client.logout()
        self.assertTrue(self.client.login(username='alice', password='Test-stock-2026!'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))

    def test_dashboard_is_scoped_and_totals_are_exact(self):
        response = self.client.get('/')
        self.assertContains(response, 'Savon')
        self.assertNotContains(response, 'Article secret')
        self.assertEqual(response.context['stats']['value'], Decimal('25'))
        self.assertEqual(response.context['stats']['total_quantity'], 10)

    def test_filters(self):
        self.assertContains(self.client.get('/?q=sav&category=Hygiène'), 'Savon')
        self.assertNotContains(self.client.get('/?q=introuvable'), '<b>Savon</b>', html=True)
        self.assertEqual(self.client.get('/?low=1').context['page_obj'].paginator.count, 0)

    def test_create_with_initial_audit(self):
        response = self.client.post(reverse('article_create'), {'name': 'Riz', 'category': 'Alimentation', 'price': '12.30', 'quantity': '6', 'alert': '2'})
        self.assertRedirects(response, '/')
        article = Article.objects.get(name='Riz')
        self.assertEqual(article.enterprise, self.company)
        self.assertEqual(article.movements.get().balance, 6)

    def test_negative_price_and_quantity_rejected(self):
        response = self.client.post(reverse('article_create'), {'name': 'Invalide', 'price': '-1', 'quantity': '-2', 'alert': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Article.objects.filter(name='Invalide').exists())

    def test_edit_does_not_change_stock(self):
        response = self.client.post(reverse('article_edit', args=[self.article.pk]), {'name': 'Savon doux', 'category': 'Hygiène', 'price': '3.00', 'quantity': '999', 'alert': '5'})
        self.assertRedirects(response, '/')
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 10)
        self.assertEqual(self.article.name, 'Savon doux')
        self.assertEqual(self.article.price, Decimal('3.00'))

    def test_sale_and_restock(self):
        movement = self.move()
        self.assertEqual((movement.delta, movement.balance, movement.unit_price), (-3, 7, Decimal('2.50')))
        self.move('in', 8)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 15)

    def test_overselling_rejected_without_audit(self):
        with self.assertRaises(ValidationError):
            self.move(quantity=11)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 10)
        self.assertEqual(Movement.objects.count(), 0)

    def test_second_sale_cannot_spend_same_stock(self):
        self.move(quantity=7)
        with self.assertRaises(ValidationError):
            self.move(quantity=7)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 3)

    def test_failed_audit_rolls_back_stock(self):
        with patch('stock.services.Movement.objects.create', side_effect=IntegrityError('audit failed')):
            with self.assertRaises(IntegrityError):
                self.move()
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 10)

    def test_invalid_movements(self):
        for kind, qty in [('invalid', 1), ('in', 0), ('out', -1), ('in', MAX_QUANTITY)]:
            with self.assertRaises(ValidationError):
                self.move(kind, qty)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 10)

    def test_movement_screen_validation(self):
        url = reverse('movement', args=[self.article.pk])
        response = self.client.post(url, {'kind': 'sale', 'quantity': 11})
        self.assertContains(response, 'Stock insuffisant')
        self.assertRedirects(self.client.post(url, {'kind': 'sale', 'quantity': 2}), '/')
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantity, 8)

    def test_other_company_object_access_denied(self):
        for name in ['article_edit', 'article_archive', 'movement', 'photo']:
            url = reverse(name, args=[self.private.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            if name != 'photo':
                self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.private.refresh_from_db()
        self.assertEqual(self.private.quantity, 100)

    def test_archive_requires_zero_and_preserves_history(self):
        url = reverse('article_archive', args=[self.article.pk])
        self.client.post(url)
        self.article.refresh_from_db()
        self.assertFalse(self.article.archived)
        self.move('out', 10)
        self.assertRedirects(self.client.post(url), '/')
        self.article.refresh_from_db()
        self.assertTrue(self.article.archived)
        self.assertEqual(self.article.movements.count(), 1)
        self.assertContains(self.client.get(reverse('history')), 'Savon (archivé)')
        self.assertEqual(self.client.get(reverse('article_edit', args=[self.article.pk])).status_code, 404)
        with self.assertRaises(ValidationError):
            self.move('in', 1)

    def test_csv_scope_and_formula_protection(self):
        self.article.name = '=HYPERLINK("bad")'
        self.article.save()
        response = self.client.get(reverse('export'))
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1][0].startswith("'="))
        self.assertEqual(rows[1][4], 'CDF')
        filtered = self.client.get(reverse('export') + '?q=introuvable')
        self.assertEqual(len(list(csv.reader(io.StringIO(filtered.content.decode('utf-8-sig')), delimiter=';'))), 1)

    def test_history_scope_and_price_snapshot(self):
        self.move()
        self.article.price = 999
        self.article.save()
        Movement.objects.create(article=self.private, actor=self.other, kind='in', delta=1, balance=101, note='Confidentiel')
        response = self.client.get(reverse('history'))
        self.assertNotContains(response, 'Confidentiel')
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['page_obj'][0].unit_price, Decimal('2.50'))

    def test_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse('movement', args=[self.article.pk]), {'kind':'sale','quantity':1}).status_code, 403)

    def test_names_are_html_escaped(self):
        self.article.name = '<script>alert(1)</script>'
        self.article.save()
        response = self.client.get('/')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_photo_upload_and_private_access(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            data = io.BytesIO()
            Image.new('RGB', (20, 20), 'purple').save(data, 'PNG')
            response = self.client.post(reverse('article_create'), {'name': 'Photo', 'price': 5, 'quantity': 1, 'alert': 0, 'photo': SimpleUploadedFile('test.png', data.getvalue(), content_type='image/png')})
            self.assertRedirects(response, '/')
            article = Article.objects.get(name='Photo')
            response = self.client.get(reverse('photo', args=[article.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            response.close()
            self.client.force_login(self.other)
            self.assertEqual(self.client.get(reverse('photo', args=[article.pk])).status_code, 404)

    def test_non_image_upload_rejected(self):
        response = self.client.post(reverse('article_create'), {'name': 'Bad photo', 'price': 5, 'quantity': 1, 'alert': 0, 'photo': SimpleUploadedFile('bad.png', b'not an image', content_type='image/png')})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Article.objects.filter(name='Bad photo').exists())

    def test_pagination(self):
        Article.objects.bulk_create([Article(enterprise=self.company, name=f'Article {i}') for i in range(25)])
        response = self.client.get('/')
        self.assertEqual(len(response.context['page_obj']), 24)
        self.assertEqual(len(self.client.get('/?page=2').context['page_obj']), 2)

    def test_demo_command(self):
        call_command('seed_demo', stdout=io.StringIO())
        self.assertEqual(Article.objects.filter(enterprise__owner__username='demo').count(), 6)
        self.assertTrue(self.client.login(username='demo', password='StockPME-demo-2026!'))
