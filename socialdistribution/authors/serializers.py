from rest_framework import serializers
from django.urls import reverse
from .models import Author

class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Author model, used in the API to convert author instances
    to JSON and vice versa.
    """
    type = serializers.CharField(default="author")
    id = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    displayName = serializers.CharField(source="display_name")
    github = serializers.CharField(allow_blank=True)
    profileImage = serializers.CharField(source="profile_image", allow_blank=True)
    web = serializers.SerializerMethodField()

    class Meta:
        """
        Determines which model and fields to serialize
        """
        model = Author
        fields = ["type", "id", "host", "displayName", "github", "profileImage", "web"]

    def get_id(self, obj):
        """
        Returns the full URL of the author for the API endpoint
        """
        request = self.context.get("request")
        return request.build_absolute_uri(reverse("authors_api:author-detail", args=[obj.id]))

    def get_host(self,obj):
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
        return request.build_absolute_uri(reverse("authors:profile_detail", args=[obj.id]))