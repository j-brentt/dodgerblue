from django.contrib import admin
from .models import Entry, Comment, RemoteNode

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
    
@admin.register(RemoteNode)
class RemoteNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'username', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'base_url', 'username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Node Information', {
            'fields': ('name', 'base_url', 'is_active')
        }),
        ('Authentication Credentials', {
            'fields': ('username', 'password'),
            'description': 'Credentials for HTTP Basic Auth. Remote node will use these to authenticate.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
