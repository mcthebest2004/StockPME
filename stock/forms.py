from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Article, Enterprise, Movement, MAX_QUANTITY

class SignupForm(UserCreationForm):
    company_name = forms.CharField(label='Nom de l’entreprise', max_length=120)
    currency = forms.ChoiceField(label='Devise', choices=Enterprise.CURRENCIES)
    class Meta:
        model = User
        fields = ['company_name', 'currency', 'username', 'password1', 'password2']

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['photo', 'name', 'category', 'price', 'quantity', 'alert']
        widgets = {'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}), 'photo': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}), 'category': forms.TextInput(attrs={'list': 'categories'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields.pop('quantity')
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'image'):
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('La photo ne doit pas dépasser 5 Mo.')
            if photo.image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError('Choisissez une image JPEG, PNG ou WebP.')
            if photo.image.width * photo.image.height > 20_000_000:
                raise forms.ValidationError('La photo ne doit pas dépasser 20 millions de pixels.')
            photo.seek(0)
            try:
                with Image.open(photo) as source:
                    image = ImageOps.exif_transpose(source).convert('RGB')
                    output = BytesIO()
                    image.save(output, format='JPEG', quality=90)
            except (OSError, ValueError) as exc:
                raise forms.ValidationError('Cette image est endommagée. Choisissez une autre photo.') from exc
            return SimpleUploadedFile('photo.jpg', output.getvalue(), content_type='image/jpeg')
        return photo

class MovementForm(forms.Form):
    kind = forms.ChoiceField(label='Type de mouvement', choices=Movement.KINDS[1:])
    quantity = forms.IntegerField(label='Quantité', min_value=1, max_value=MAX_QUANTITY)
    note = forms.CharField(label='Référence / commentaire', max_length=240, required=False, widget=forms.TextInput(attrs={'placeholder': 'Ex : facture V-2026-001, fournisseur…'}))
