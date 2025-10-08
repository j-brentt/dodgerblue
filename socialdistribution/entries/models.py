from django.db import models

from authors.models import Author
import uuid

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
        #('image/png;base64', 'PNG Image'),
       # ('image/jpeg;base64', 'JPEG Image'),
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
    
    # Visibility settings
    visibility = models.CharField(
        max_length=10, 
        choices=VISIBILITY_CHOICES, 
        default='PUBLIC'
    )
    
    # Timestamps
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published']  # Most recent first
        verbose_name_plural = 'Entries'
    
    def __str__(self):
        return f"{self.title} by {self.author.display_name}"

