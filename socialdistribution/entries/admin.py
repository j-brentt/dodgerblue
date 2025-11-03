from django.contrib import admin
from .models import Entry, Comment

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'visibility', 'content_type', 'published', 'updated')
    list_filter = ('visibility', 'content_type', 'published')
    search_fields = ('title', 'description', 'author__username', 'author__display_name')
    ordering = ('-published',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('entry', 'author', 'created_at', 'likes_count')
    list_filter = ('created_at',)
    search_fields = ('entry__title', 'author__username', 'content')
    ordering = ('-created_at',)

    def likes_count(self, obj):
        return obj.likes_count
