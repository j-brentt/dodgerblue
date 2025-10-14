from django.urls import path
from . import views

app_name = 'entries'

urlpatterns = [
    path('create/', views.create_entry, name='create_entry'),
    path('my_entries/', views.my_entries, name='my_entries'),
    path('<str:entry_id>/', views.view_entry, name='view_entry'),
    path('<str:entry_id>/edit/', views.edit_entry, name='edit_entry'),
    path('<str:entry_id>/delete/', views.delete_entry, name='delete_entry'),
    path("public/", views.PublicEntriesListView.as_view(), name="public_entries"),
    path("<int:pk>/", views.view_entry, name="view_entry"),
]