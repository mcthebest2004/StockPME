import csv
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Sum, Count, Q, DecimalField, ExpressionWrapper
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_GET
from .forms import ArticleForm, MovementForm, SignupForm
from .models import Article, Enterprise, Movement
from .services import record_movement

def company(request):
    return get_object_or_404(Enterprise, owner=request.user)

def inventory(enterprise, request):
    rows = Article.objects.filter(enterprise=enterprise, archived=False)
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    if query:
        rows = rows.filter(Q(name__icontains=query) | Q(category__icontains=query))
    if category:
        rows = rows.filter(category=category)
    if request.GET.get('low') == '1':
        rows = rows.filter(quantity__lte=F('alert'))
    return rows

@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Enterprise.objects.create(owner=user, name=form.cleaned_data['company_name'], currency=form.cleaned_data['currency'])
        login(request, user)
        messages.success(request, 'Votre entreprise est prête. Ajoutez votre premier article.')
        return redirect('dashboard')
    return render(request, 'registration/signup.html', {'form': form})

@login_required
@require_GET
def dashboard(request):
    enterprise = company(request)
    all_items = Article.objects.filter(enterprise=enterprise, archived=False)
    value = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=24, decimal_places=2))
    stats = all_items.aggregate(count=Count('pk'), total_quantity=Sum('quantity'), value=Sum(value), low=Count('pk', filter=Q(quantity__lte=F('alert'))))
    page = Paginator(inventory(enterprise, request), 24).get_page(request.GET.get('page'))
    filters = request.GET.copy()
    filters.pop('page', None)
    return render(request, 'stock/dashboard.html', {'enterprise': enterprise, 'stats': stats, 'page_obj': page, 'categories': all_items.exclude(category='').values_list('category', flat=True).order_by('category').distinct(), 'filters': filters.urlencode(), 'section': 'stock'})

@login_required
@require_http_methods(['GET', 'POST'])
def article_form(request, pk=None):
    enterprise = company(request)
    article = get_object_or_404(Article, pk=pk, enterprise=enterprise, archived=False) if pk else Article(enterprise=enterprise)
    form = ArticleForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=article)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            obj = form.save(commit=False)
            if pk:
                # Only metadata: never overwrite a concurrently updated stock balance.
                obj.save(update_fields=['name', 'category', 'price', 'alert', 'photo'])
            else:
                obj.save()
                Movement.objects.create(article=obj, actor=request.user, kind='initial', delta=obj.quantity, balance=obj.quantity, unit_price=obj.price)
        messages.success(request, 'Article enregistré.')
        return redirect('dashboard')
    return render(request, 'stock/article_form.html', {'form': form, 'article': article, 'enterprise': enterprise, 'section': 'stock', 'categories': Article.objects.filter(enterprise=enterprise, archived=False).exclude(category='').values_list('category', flat=True).order_by('category').distinct()})

@login_required
@require_http_methods(['GET', 'POST'])
def archive(request, pk):
    enterprise = company(request)
    article = get_object_or_404(Article, pk=pk, enterprise=enterprise, archived=False)
    if request.method == 'POST':
        changed = Article.objects.filter(pk=article.pk, archived=False, quantity=0).update(archived=True)
        if changed:
            messages.success(request, 'Article archivé. Son historique reste disponible.')
            return redirect('dashboard')
        messages.error(request, 'Le stock doit être à zéro avant d’archiver cet article. Enregistrez d’abord une sortie.')
    return render(request, 'stock/archive.html', {'article': article, 'enterprise': enterprise})

@login_required
@require_http_methods(['GET', 'POST'])
def movement(request, pk):
    enterprise = company(request)
    article = get_object_or_404(Article, pk=pk, enterprise=enterprise, archived=False)
    form = MovementForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            record_movement(article_id=article.pk, enterprise=enterprise, actor=request.user, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
            article.refresh_from_db()
        else:
            messages.success(request, 'Mouvement enregistré et stock mis à jour.')
            return redirect('dashboard')
    return render(request, 'stock/movement.html', {'form': form, 'article': article, 'enterprise': enterprise, 'section': 'stock'})

@login_required
@require_GET
def history(request):
    enterprise = company(request)
    rows = Movement.objects.filter(article__enterprise=enterprise).select_related('article', 'actor')
    if request.GET.get('q'):
        rows = rows.filter(Q(article__name__icontains=request.GET['q']) | Q(note__icontains=request.GET['q']))
    if request.GET.get('kind'):
        rows = rows.filter(kind=request.GET['kind'])
    filters = request.GET.copy()
    filters.pop('page', None)
    return render(request, 'stock/history.html', {'enterprise': enterprise, 'page_obj': Paginator(rows, 30).get_page(request.GET.get('page')), 'kinds': Movement.KINDS, 'filters': filters.urlencode(), 'section': 'history'})

def csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text

@login_required
@require_GET
def export_csv(request):
    enterprise = company(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="stockpme-stock.csv"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Article', 'Catégorie', 'Quantité', 'Prix unitaire', 'Devise', 'Valeur', 'Seuil d’alerte'])
    for item in inventory(enterprise, request).iterator():
        writer.writerow([csv_safe(item.name), csv_safe(item.category), item.quantity, item.price, enterprise.currency, item.quantity * item.price, item.alert])
    return response

@login_required
@require_GET
def photo(request, pk):
    article = get_object_or_404(Article, pk=pk, enterprise__owner=request.user)
    if not article.photo:
        raise Http404
    try:
        response = FileResponse(article.photo.open('rb'))
        response['Cache-Control'] = 'private, no-store'
        return response
    except FileNotFoundError:
        raise Http404
