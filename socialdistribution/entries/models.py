from django.db import models
from django.contrib.auth import get_user_model

from authors.models import Author, FollowRequest, FollowRequestStatus
import uuid

User = get_user_model()

class Visibility(models.TextChoices):
    PUBLIC = "PUBLIC", "Public"
    FRIENDS = "FRIENDS", "Friends only"
    DELETED = "DELTED", "Deleted"
    UNLISTED = "UNLISTED", "Unlisted"

class Entry(models.Model):
    """Model for blog entries/posts"""
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('FRIENDS', 'Friends Only'),
        ('UNLISTED', 'Unlisted'),
        ('DELETED', 'Deleted'),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown'), 
        ('image/png;base64', 'PNG Image'),
        ('image/jpeg;base64', 'JPEG Image'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Entry content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Brief description of the entry")
    content = models.TextField(help_text="Main content of the entry")
    content_type = models.CharField(
        max_length=50, 
        choices=CONTENT_TYPE_CHOICES, 
        default='text/plain'
    )
    liked_by = models.ManyToManyField(User, related_name='liked_entries', blank=True)
    
    @property
    def likes_count(self):
        return self.liked_by.count()    
   
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='entries')
    
   # Unique identifier for the entry
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    
    # To keep track of which GitHub activity this entry came from
    source_id = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    unique=True,
)

    def can_view(self, user) -> bool:
        """
        Returns True if the given user can view this entry.
        Anyone can view public, no one can view deleted, friends only means both follow eachother
        TODO: Utilize more in next iteration
        """
        if self.visibility == Visibility.PUBLIC:
            return True

        if self.visibility == Visibility.DELETED:
            return False

        # Unlisted posts — visible to anyone with the link (even if not logged in)
        if self.visibility == Visibility.UNLISTED:
            return True
        
        if not user or not user.is_authenticated:
            return False

        if user == self.author:
            return True

        # Mutual following for FRIENDS
        if self.visibility == Visibility.FRIENDS:
            viewer_follows_author = FollowRequest.objects.filter(
                follower=user,
                followee=self.author,
                status=FollowRequestStatus.APPROVED
            ).exists()
            author_follows_viewer = FollowRequest.objects.filter(
                follower=self.author,
                followee=user,
                status=FollowRequestStatus.APPROVED
            ).exists()
            return viewer_follows_author and author_follows_viewer

        # Followers-only for UNLISTED
        if self.visibility == Visibility.UNLISTED:
            viewer_follows_author = FollowRequest.objects.filter(
                follower=user,
                followee=self.author,
                status=FollowRequestStatus.APPROVED
            ).exists()
            return viewer_follows_author

        return False

    # Timestamps
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published']  # Most recent first
        verbose_name_plural = 'Entries'
    
    def __str__(self):
        return f"{self.title} by {self.author.display_name}"


class Comment(models.Model):
    """User-submitted comment attached to an entry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    liked_by = models.ManyToManyField(
        User,
        related_name="liked_comments",
        blank=True,
    )

    @property
    def likes_count(self):
        return self.liked_by.count()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.entry}"

class RemoteNode(models.Model):
    """Stores credentials for connecting to other team's nodes"""
    name = models.CharField(max_length=100, unique=True)  # "Team Blue"
    base_url = models.URLField(help_text="e.g., https://team-dodgerblue.herokuapp.com") # Host URL
    username = models.CharField(max_length=100, blank=True, default='', help_text="Username they gave us")
    password = models.CharField(max_length=100, blank=True, default='', help_text="Password they gave us")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.base_url})"
    
    class Meta:
        verbose_name = "Remote Node"
        verbose_name_plural = "Remote Nodes"