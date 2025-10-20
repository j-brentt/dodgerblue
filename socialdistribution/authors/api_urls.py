from django.urls import path
from .api_views import AuthorDetailView, AuthorListView

app_name = "authors_api"

urlpatterns = [
    path('authors/<uuid:pk>/', AuthorDetailView.as_view(), name='author-detail'),
    path('authors/', AuthorListView.as_view(), name='authors-list'),
]
