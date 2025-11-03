from django.urls import path
from .views import upload_image
from .api_views import (
    PublicEntriesListView,
    EntryDetailView,
    MyEntriesListView,
    EntryEditDeleteView,
    EntryLikesListView,
    AuthorEntryLikesListView,
    CommentLikesListView,
    AuthorLikedListView,
    AuthorLikedFQIDView,
    AuthorLikedDetailView,
    LikeDetailView,
    EntryCommentsListCreateView,
    CommentDetailView,
    CommentLikeView,
    render_markdown_entry,
)

app_name = "api"

urlpatterns = [
    path("entries/", PublicEntriesListView.as_view(), name="entries-list"),
    path("entries/<uuid:entry_id>/", EntryDetailView.as_view(), name="entry-detail"),
    path("author/<uuid:author_id>/entries/", MyEntriesListView.as_view(), name="author-entries"),
    path("entries/<uuid:entry_id>/likes/", EntryLikesListView.as_view(), name="entry-likes"),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/likes/",
        AuthorEntryLikesListView.as_view(),
        name="author-entry-likes",
    ),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/comments/<uuid:comment_id>/likes/",
        CommentLikesListView.as_view(),
        name="author-entry-comment-likes",
    ),
    path("authors/<uuid:author_id>/liked/", AuthorLikedListView.as_view(), name="author-liked"),
    path("authors/<path:author_fqid>/liked/", AuthorLikedFQIDView.as_view(), name="author-liked-fqid"),
    path(
        "authors/<uuid:author_id>/liked/<str:like_id>/",
        AuthorLikedDetailView.as_view(),
        name="author-liked-detail",
    ),
    path("liked/<str:like_id>/", LikeDetailView.as_view(), name="liked-detail"),
    path("entries/<uuid:entry_id>/edit/", EntryEditDeleteView.as_view(), name="entry_edit"),
    path("entries/<uuid:entry_id>/comments/", EntryCommentsListCreateView.as_view(), name="entry-comments"),
    path("comments/<uuid:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path("comments/<uuid:comment_id>/like/", CommentLikeView.as_view(), name="comment-like"),
    path("upload-image/", upload_image, name="upload_image"),
    path('entries/<uuid:entry_id>/rendered/', render_markdown_entry, name='entry-rendered'),
]
