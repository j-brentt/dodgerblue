from django.db import models
from django.contrib.auth import get_user_model

from authors.models import Author, FollowRequest, FollowRequestStatus
import uuid

User = get_user_model()

class Visibility(models.TextChoices):
    PUBLIC = "PUBLIC", "Public"
    FRIENDS = "FRIENDS", "Friends only"
    DELETED = "DELTED", "Deleted"

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
       # ('text/markdown', 'Markdown'), 
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
    
   
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='entries')
    
   # Unique identifier for the entry
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    
    def can_view(self, user) -> bool:
        """
        Returns True if the given user can view this entry.
        Anyone can view public, no one can view deleted, friends only means both follow eachother
        TODO: Utilize more in next iteration
        """
        # Public entries are always visible
        if self.visibility == Visibility.PUBLIC:
            return True

        # Deleted entries are never visible
        if self.visibility == Visibility.DELETED:
            return False

        # Must be authenticated for FRIENDS entries
        if not user or not user.is_authenticated:
            return False

        # Author can always view
        if user == self.author:
            return True
        viewer_author = user 

        # Only check mutual following for FRIENDS visibility
        if self.visibility == Visibility.FRIENDS:
            # Viewer follows author
            viewer_follows_author = FollowRequest.objects.filter(
                follower=viewer_author,
                followee=self.author,
                status=FollowRequestStatus.APPROVED
            ).exists()

            # Author follows viewer
            author_follows_viewer = FollowRequest.objects.filter(
                follower=self.author,
                followee=viewer_author,
                status=FollowRequestStatus.APPROVED
            ).exists()

            return viewer_follows_author and author_follows_viewer

        # Fallback: deny access
        return False
    

    # Timestamps
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published']  # Most recent first
        verbose_name_plural = 'Entries'
    
    def __str__(self):
        return f"{self.title} by {self.author.display_name}"

