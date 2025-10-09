from django.contrib import admin
from .models import Author

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_approved', 'is_active', 'is_staff')
    list_filter = ('is_approved', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
