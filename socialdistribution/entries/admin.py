from django.contrib import admin
from .models import Entry

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'visibility', 'content_type', 'published', 'updated')
    list_filter = ('visibility', 'content_type', 'published')
    search_fields = ('title', 'description', 'author__username', 'author__display_name')
    ordering = ('-published',)