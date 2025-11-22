from django.urls import path
from .api_views import AuthorDetailView, AuthorListView, followers_list_api,followers_detail_api
from . import api_views
app_name = "authors_api"

urlpatterns = [
    path('authors/<uuid:pk>/', AuthorDetailView.as_view(), name='author-detail'),
    path('authors/', AuthorListView.as_view(), name='authors-list'),
    path('authors/explore/', api_views.ExploreAuthorsView.as_view(), name='explore-authors'),
    path('authors/follow/', api_views.api_follow_author, name='api-follow'),
    path('authors/<uuid:author_id>/follow-status/', api_views.check_follow_status, name='follow-status'),
    path('authors/<uuid:author_id>/unfollow/', api_views.api_unfollow_author, name='api-unfollow'),
    path(
        "authors/<uuid:author_id>/followers",
        followers_list_api,
        name="followers-list-api",
    ),
    path(
        "authors/<uuid:author_id>/followers/<path:foreign_author_fqid>",
        followers_detail_api,
        name="followers-detail-api",
    ),
]
