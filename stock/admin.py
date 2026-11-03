from django.contrib import admin
from .models import Enterprise, Article, Movement

@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'currency']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    readonly_fields = ['owner', 'currency']

class AuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Article)
class ArticleAdmin(AuditAdmin):
    list_display = ['name', 'enterprise', 'category', 'quantity', 'price', 'archived']
    list_filter = ['enterprise', 'archived']
    search_fields = ['name', 'category']

@admin.register(Movement)
class MovementAdmin(AuditAdmin):
    list_display = ['article', 'kind', 'delta', 'balance', 'actor', 'created_at']
    list_filter = ['kind']
