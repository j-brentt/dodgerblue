from django.db import models
from django.contrib.auth import get_user_model

from authors.models import Author
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

    # Permissions
    def can_view(self, user) -> bool:
        # Public is visible to all (including anonymous)
        if self.visibility == Visibility.PUBLIC:
            return True

        # Friends-only: owner can see
        if user and user.is_authenticated:
            if user == self.author:
                return True
            # Try to resolve the author's Author record from the user
            viewer_author = getattr(user, "author", None)
            if viewer_author is not None:
                if viewer_author == self.author:
                    return True

                # Support either an Author.is_friends_with(other) helper
                # or a ManyToMany named `friends` on Author, if it exists.
                if hasattr(self.author, "is_friends_with"):
                    return self.author.is_friends_with(viewer_author)
                if hasattr(self.author, "friends"):
                    try:
                        return self.author.friends.filter(pk=viewer_author.pk).exists()
                    except Exception:
                        pass

        return False
    
    # Timestamps
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published']  # Most recent first
        verbose_name_plural = 'Entries'
    
    def __str__(self):
        return f"{self.title} by {self.author.display_name}"

