from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('connexion/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('inscription/', views.signup, name='signup'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='logout'),
    path('articles/nouveau/', views.article_form, name='article_create'),
    path('articles/<int:pk>/modifier/', views.article_form, name='article_edit'),
    path('articles/<int:pk>/archiver/', views.archive, name='article_archive'),
    path('articles/<int:pk>/mouvement/', views.movement, name='movement'),
    path('articles/<int:pk>/photo/', views.photo, name='photo'),
    path('historique/', views.history, name='history'),
    path('export/', views.export_csv, name='export'),
]
