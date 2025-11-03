from django.urls import path
from . import api_views
from .views import upload_image


app_name = "api"

urlpatterns = [
    path('entries/', api_views.PublicEntriesListView.as_view(), name='entries-list'),
    path('entries/<uuid:entry_id>/', api_views.EntryDetailView.as_view(), name='entry-detail'),
    path('author/<uuid:author_id>/entries/', api_views.MyEntriesListView.as_view(), name='author-entries'),
    path("entries/<uuid:entry_id>/likes/", api_views.EntryLikesListView.as_view(), name="entry-likes"),
    path('entries/<uuid:entry_id>/edit/',api_views.EntryEditDeleteView.as_view(),name='entry_edit'),
    path('upload-image/', upload_image, name='upload_image'),
]
