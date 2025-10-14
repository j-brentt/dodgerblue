from django.db import models
from  django.contrib.auth.models import AbstractUser
from django.urls import reverse
import uuid

class Author(AbstractUser):
    """
    Custom user model for authors 
    """
    # Generate random id for primary key
    id = models.UUIDField(primary_key = True, default=uuid.uuid4, editable = False)

    # Profile information
    display_name = models.CharField(max_length = 39)
    github = models.URLField(blank = True, null=True, help_text="GitHub profile url")
    profile_image = models.URLField(blank=True, null=True, help_text="Profile image URL")
    
    # Admin approval for sign-ups
    is_approved = models.BooleanField(default=False, help_text="Admin has approved this user")

    # URL to author's profile - remains unique across the app
    def get_absolute_url(self):
        return reverse("authors:profile_detail", args=[self.id])
    
