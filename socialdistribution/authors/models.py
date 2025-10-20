from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
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


class FollowRequestStatus(models.TextChoices):
    """Discrete states for a follow request lifecycle."""

    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class FollowRequest(models.Model):
    """Represents a directed follow relationship that requires approval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="follow_requests_sent",
    )
    followee = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="follow_requests_received",
    )
    status = models.CharField(
        max_length=10,
        choices=FollowRequestStatus.choices,
        default=FollowRequestStatus.PENDING,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "followee"],
                name="unique_follow_request",
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F("followee")),
                name="prevent_self_follow",
            ),
        ]
        ordering = ["-created_at"]

    def approve(self):
        """Mark the follow request as approved."""
        if self.status != FollowRequestStatus.APPROVED:
            self.status = FollowRequestStatus.APPROVED
            self.save(update_fields=["status", "updated_at"])

    def reject(self):
        """Mark the follow request as rejected."""
        if self.status != FollowRequestStatus.REJECTED:
            self.status = FollowRequestStatus.REJECTED
            self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"{self.follower} → {self.followee} ({self.status})"
