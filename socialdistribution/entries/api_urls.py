from django.urls import path
from .views import upload_image
from .api_views import (
    PublicEntriesListView,
    EntryDetailView,
    MyEntriesListView,
    EntryEditDeleteView,
    EntryLikesListView,
    EntryLikeView,
    AuthorEntryLikesListView,
    CommentLikesListView,
    AuthorLikedListView,
    AuthorLikedFQIDView,
    AuthorLikedDetailView,
    EntryCommentsListCreateView,
    CommentDetailView,
    CommentLikeView,
    render_markdown_entry,
    InboxView,
    EntryImageView,
    EntryImageFQIDView,
    EntryLikesFQIDView,
    CommentFQIDView,
    CommentedListView,
    CommentedFQIDListView,
    CommentedDetailView,
    CommentedFQIDDetailView,
    FollowRequestsListView,
    EntryCommentsFQIDView,
    AuthorEntryCommentsListCreateView,
    CommentLikesFQIDView,
    LikeFQIDView,
)

app_name = "api"

urlpatterns = [
    # Entry endpoints
    path("entries/", PublicEntriesListView.as_view(), name="entries-list"),
    path("entries/<uuid:entry_id>/", EntryDetailView.as_view(), name="entry-detail"),

    # Author's Entries endpoints
    path("authors/<uuid:author_id>/entries/", MyEntriesListView.as_view(), name="author-entries"),
    path("authors/<uuid:author_id>/entries/<uuid:entry_id>/", EntryEditDeleteView.as_view(), name="author-entry-detail"), # add

    # Entry likes endpoints (and likes on comments)
    path("entries/<uuid:entry_id>/likes/", EntryLikesListView.as_view(), name="entry-likes"),
    path("entries/<uuid:entry_id>/like/", EntryLikeView.as_view(), name="entry-like"),
    path("entries/<path:entry_fqid>/likes/", EntryLikesFQIDView.as_view(), name="entry-likes-fqid"),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/likes/",
        AuthorEntryLikesListView.as_view(),
        name="author-entry-likes",
    ),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/comments/<path:comment_fqid>/likes",
        CommentLikesFQIDView.as_view(),
        name="author-entry-comment-likes-fqid",
    ),
 
    # Liked endpoints
    path("authors/<uuid:author_id>/liked/", AuthorLikedListView.as_view(), name="author-liked"),
    path("authors/<path:author_fqid>/liked/", AuthorLikedFQIDView.as_view(), name="author-liked-fqid"),
    path(
        "authors/<uuid:author_id>/liked/<str:like_id>/",
        AuthorLikedDetailView.as_view(),
        name="author-liked-detail",
    ),
    path("liked/<path:like_fqid>", LikeFQIDView.as_view(), name="liked-fqid"),

    # Comment endpoints
    path("entries/<uuid:entry_id>/comments/", EntryCommentsListCreateView.as_view(), name="entry-comments"),
    path("entries/<path:entry_fqid>/comments/", EntryCommentsFQIDView.as_view(), name="entry-comments-fqid"),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/comments",
        AuthorEntryCommentsListCreateView.as_view(),
        name="author-entry-comments"
    ),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/comment/<path:remote_comment_fqid>",
        CommentFQIDView.as_view(),
        name="author-entry-comment-fqid"
    ), # Comment via FQID

    path("comments/<uuid:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path("comments/<uuid:comment_id>/like/", CommentLikeView.as_view(), name="comment-like"),
    path(
        "authors/<uuid:author_id>/entries/<uuid:entry_id>/comments/<uuid:comment_id>/likes/",
        CommentLikesListView.as_view(),
        name="author-entry-comment-likes",
    ),

    # Commented API
    path("authors/<uuid:author_id>/commented", CommentedListView.as_view(), name="author-commented"),
    path("authors/<path:author_fqid>/commented", CommentedFQIDListView.as_view(), name="author-commented-fqid"),
    path("authors/<uuid:author_id>/commented/<uuid:comment_id>", CommentedDetailView.as_view(), name="author-commented-detail"),
    path("commented/<path:comment_fqid>", CommentedFQIDDetailView.as_view(), name="commented-fqid"),

    # Follow Request endpoints
    path("authors/<uuid:author_id>/follow_requests", FollowRequestsListView.as_view(), name="follow-requests"),

    # Inbox endpoint (which handles multiple types of objects)
    path("authors/<uuid:author_id>/inbox/", InboxView.as_view(), name="author-inbox"),
    path("authors/<uuid:author_id>/inbox", InboxView.as_view(), name="author-inbox-no-slash"),


    # Image endpoints
    path("authors/<uuid:author_id>/entries/<uuid:entry_id>/image", EntryImageView.as_view(), name="author-entry-image"),
    path("entries/<path:entry_fqid>/image", EntryImageFQIDView.as_view(), name="entry-image-fqid"),

    # Misc endpoints
    path("entries/<uuid:entry_id>/edit/", EntryEditDeleteView.as_view(), name="entry_edit"),
    path("upload-image/", upload_image, name="upload_image"),
    path('entries/<uuid:entry_id>/rendered/', render_markdown_entry, name='entry-rendered'),
]