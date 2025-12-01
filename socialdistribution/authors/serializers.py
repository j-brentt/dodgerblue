from rest_framework import serializers
from django.urls import reverse

from .models import Author


class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Author model, used in the API to convert author instances
    to JSON and vice versa.
    """

    # Computed / constant fields
    type = serializers.CharField(default="author", read_only=True)
    id = serializers.SerializerMethodField(read_only=True)
    host = serializers.SerializerMethodField(read_only=True)
    web = serializers.SerializerMethodField(read_only=True)

    # Mapped fields
    displayName = serializers.CharField(source="display_name")
    github = serializers.CharField(allow_blank=True)
    profileImage = serializers.CharField(source="profile_image", allow_blank=True)

    class Meta:
        """
        Determines which model and fields to serialize
        """
        model = Author
        fields = [
            "type",
            "id",
            "host",
            "displayName",
            "github",
            "profileImage",
            "web",
        ]

    def get_id(self, obj):
        """
        Returns the full URL of the author for the API endpoint
        """
        request = self.context.get("request")
        return request.build_absolute_uri(
            reverse("authors_api:author-detail", args=[obj.id])
        )

    def get_host(self, obj):
        """
        Used to determine which node the author lives on
        """
        request = self.context.get("request")
        return request.build_absolute_uri("/api/")

    def get_web(self, obj):
        """
        Generates the URL for the HTML page of the author
        """
        request = self.context.get("request")
        return request.build_absolute_uri(
            reverse("authors:profile_detail", args=[obj.id])
        )
    
class FollowAuthorRequestSerializer(serializers.Serializer):
    """
    Request body for POST /api/authors/follow/.
    Accepts either a UUID or a full author URL.
    """
    author_id = serializers.CharField(
        help_text="UUID or full URL of the author to follow"
    )