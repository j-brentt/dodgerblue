from rest_framework import serializers
from django.urls import reverse
from .models import Entry
from authors.serializers import AuthorSerializer
from rest_framework import serializers
from django.urls import reverse
from .models import Entry, Comment
from authors.serializers import AuthorSerializer

class EntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the Entry model, used in the API to convert Entry instances
    to JSON and vice versa. Includes nested author information.
    """
    type = serializers.CharField(default="entry", read_only=True)
    id = serializers.SerializerMethodField()
    web = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    contentType = serializers.CharField(source="content_type")
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        """
        Used to determine which model and fields of the model to serialize
        """
        model = Entry
        fields = [
            "type",
            "id",
            "web",
            "title",
            "description",
            "contentType",
            "content",
            "visibility",
            "published",
            "author",
            "comments",
            "likes",
        ]

    def get_id(self, obj):
        """
        Generate full URL for the API endpoint of the entry
        """
        request = self.context.get("request")
        return request.build_absolute_uri(
            reverse("api:entry-detail", args=[obj.id])
        )

    def get_web(self, obj):
        """
        Generates the URL for the HTML page of the entry
        """
        request = self.context.get("request")
        return request.build_absolute_uri(
            reverse("entries:view_entry", args=[obj.id])
        )

    

    def get_likes(self, obj):
        request = self.context.get("request")
        likes_qs = obj.liked_by.all()
        page = int(request.query_params.get("like_page", 1))
        size = int(request.query_params.get("like_size", 50))
        start = (page - 1) * size
        end = start + size
        entry_api_url = self.get_id(obj)
        entry_html_url = self.get_web(obj)
        likes_url = request.build_absolute_uri(
            reverse("api:entry-likes", args=[obj.id])
        )
        likes_page = likes_qs[start:end]
        src = []
        for author in likes_page:
            src.append(
                {
                    "type": "like",
                    "author": AuthorSerializer(
                        author, context={"request": request}
                    ).data,
                    "published": obj.updated,
                    "id": f"{likes_url}{author.id}/",
                    "object": entry_html_url,
                }
            )
        return {
            "type": "likes",
            "web": entry_html_url,
            "id": likes_url,
            "page_number": page,
            "size": size,
            "count": likes_qs.count(),
            "src": src,
        }
    
    def get_comments(self, obj):
        """
        Retrieve and serialize the comments for the entry.
        """
        request = self.context.get("request")
        comments_qs = obj.comments.all()  # Assuming `comments` is the related name for the Comment model
        page = int(request.query_params.get("comment_page", 1))
        size = int(request.query_params.get("comment_size", 50))
        start = (page - 1) * size
        end = start + size
        comments_page = comments_qs[start:end]
        comments_url = request.build_absolute_uri(
            reverse("api:entry-comments", args=[obj.id])
        )
        return {
            "type": "comments",
            "id": comments_url,
            "page_number": page,
            "size": size,
            "count": comments_qs.count(),
            "src": CommentSerializer(comments_page, many=True, context={"request": request}).data,
        }


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comment objects exposed via the API."""

    type = serializers.CharField(default="comment", read_only=True)
    id = serializers.SerializerMethodField()
    entry = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    published = serializers.DateTimeField(source="created_at", read_only=True)
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "type",
            "id",
            "entry",
            "author",
            "content",
            "published",
            "likes",
        ]

    def get_id(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(reverse("api:comment-detail", args=[obj.id]))
        return str(obj.id)

    def get_entry(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(reverse("api:entry-detail", args=[obj.entry_id]))
        return str(obj.entry_id)

    def get_likes(self, obj):
        return obj.likes_count
