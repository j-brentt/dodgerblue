from rest_framework import generics, permissions
from authors.models import Author
from authors.serializers import AuthorSerializer

class AuthorDetailView(generics.RetrieveAPIView):
    """
    GET /api/author/<id>
    Used to retreive the author detials and serialize them
    Accessible to anyone (Accounts are public)
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]

class AuthorListView(generics.ListAPIView):
    """
    GET /api/authors/
    Returns a list of all authors (public accounts).
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]