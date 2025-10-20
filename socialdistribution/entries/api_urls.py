from django.urls import path
from . import api_views

app_name = "api"

urlpatterns = [
    path('entries/', api_views.PublicEntriesListView.as_view(), name='entries-list'),
    path('entries/<uuid:entry_id>/', api_views.EntryDetailView.as_view(), name='entry-detail'),
    path('author/<uuid:author_id>/entries/', api_views.MyEntriesListView.as_view(), name='author-entries'),
    path('entries/<uuid:entry_id>/edit/',api_views.EntryEditDeleteView.as_view(),name='entry_edit'),
]
