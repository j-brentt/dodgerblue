from rest_framework import serializers
from django.urls import reverse
from .models import Entry
from authors.serializers import AuthorSerializer

class EntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the Entry model, used in the API to convert Entry instances
    to JSON and vice versa. Includes nested author information.
    """
    type = serializers.CharField(default="entry", read_only = True)
    id = serializers.SerializerMethodField()
    web = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)

    class Meta:
        """
        Used to determine which model and fields of the model to serialize
        """
        model = Entry
        fields = [
            "type", "id", "web", "title", "description", "content_type", "content",
            "visibility", "published", "author"
        ]

    def get_id(self, obj):
        """
        Generate full URL for the API endpoint of the entry
        """
        request = self.context.get("request")
        return request.build_absolute_uri(reverse("api:entry-detail", args=[obj.id]))

    def get_web(self, obj):
        """
        Generatesthe URL for the HTML page of the entry
        """
        request = self.context.get("request")
        return request.build_absolute_uri(reverse("entries:view_entry", args=[obj.id]))
