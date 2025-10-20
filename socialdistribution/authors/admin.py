from django.contrib import admin
from .models import Author, FollowRequest

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_approved', 'is_active', 'is_staff')
    list_filter = ('is_approved', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')


@admin.register(FollowRequest)
class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followee', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('follower__username', 'followee__username')
