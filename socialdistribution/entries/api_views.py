from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import base64
import binascii
from urllib.parse import unquote
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.db.models import Q
from django.urls import reverse
from .models import Entry, Visibility, Comment, RemoteNode
from authors.models import FollowRequest, FollowRequestStatus, Author
from authors.serializers import AuthorSerializer
from .serializers import EntrySerializer, CommentSerializer
from django.http import JsonResponse
import commonmark
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.utils import timezone
from dateutil import parser as date_parser
import requests
from requests.auth import HTTPBasicAuth
from socialdistribution.authentication import RemoteNodeBasicAuthentication, HybridAuthentication
from socialdistribution.pagination import CustomPageNumberPagination
from typing import Optional
from socialdistribution.permissions import IsAuthenticatedNodeOrLocalUser
from django.conf import settings
import requests
import mimetypes
from requests.auth import HTTPBasicAuth
from django.utils import timezone
from authors.models import FollowRequest, FollowRequestStatus, Author
from entries.models import Entry, Visibility, RemoteNode


def resolve_author_or_404(identifier: str) -> Author:
    decoded = unquote(identifier).strip()
    candidates = []
    if decoded:
        candidates.append(decoded)

    trimmed = decoded.rstrip("/")
    if trimmed and trimmed not in candidates:
        candidates.append(trimmed)

    if "/" in trimmed:
        last_segment = trimmed.split("/")[-1]
        if last_segment and last_segment not in candidates:
            candidates.append(last_segment)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return Author.objects.get(id=candidate)
        except (Author.DoesNotExist, ValueError):
            continue

    raise Http404("Author not found")


def _resolve_remote_author_from_data(author_data: dict) -> Optional[Author]:
    """
    Given the 'author' object from a remote payload, return a local Author instance
    (create a local stub if needed). Returns None on invalid/missing id.
    This version uses the author's UUID to build a collision-resistant username and
    handles IntegrityError when creating the local Author.
    """
    if not isinstance(author_data, dict):
        return None

    full_id = (author_data.get("id") or "").rstrip("/")
    if not full_id:
        return None

    # extract UUID-like last segment
    try:
        import uuid as _uuid
        uuid_str = full_id.split("/")[-1]
        _uuid.UUID(uuid_str)
    except Exception:
        return None

    display_name = (
        author_data.get("displayName")
        or author_data.get("display_name")
        or author_data.get("username")
        or f"remote_{uuid_str[:8]}"
    )

    # Build a collision-resistant username using the uuid
    username = f"remote_{uuid_str.replace('-', '')[:24]}"

    raw_host = (author_data.get("host") or "").rstrip("/")
    if raw_host.endswith("/api"):
        host = raw_host[:-4]
    else:
        host = raw_host or None

    # Try to get by id first (preferred). If not present, create safely.
    try:
        remote_author = Author.objects.filter(id=uuid_str).first()
        if remote_author:
            # Ensure host is set if we have it
            if host and not getattr(remote_author, "host", None):
                remote_author.host = host
                remote_author.save(update_fields=["host"])
            return remote_author

        # Create with collision-resistant username; catch IntegrityError and retry with suffix
        from django.db import IntegrityError, transaction

        for attempt in range(3):
            try:
                with transaction.atomic():
                    remote_author = Author.objects.create(
                        id=uuid_str,
                        username=username if attempt == 0 else f"{username}_{attempt}",
                        display_name=display_name,
                        github=author_data.get("github", "") or "",
                        profile_image=author_data.get("profileImage", "") or author_data.get(
                            "profile_image", "") or "",
                        is_active=False,
                        host=host,
                    )
                return remote_author
            except IntegrityError:
                # Username collision — try another suffix
                continue

        # If still failing, fallback to looking up by username or return None
        remote_author = Author.objects.filter(
            username__startswith=f"remote_{uuid_str.replace('-', '')[:16]}").first()
        return remote_author
    except Exception:
        # Keep callers responsible for returning HTTP 400/500; here return None on failure
        return None


LIKE_ID_SEPARATOR = "|"


def encode_like_identifier(object_type: str, object_id: str, author_id: str) -> str:
    raw_value = f"{object_type}{LIKE_ID_SEPARATOR}{object_id}{LIKE_ID_SEPARATOR}{author_id}"
    return base64.urlsafe_b64encode(raw_value.encode("utf-8")).decode("ascii").rstrip("=")


def decode_like_identifier(identifier: str) -> tuple[str, str, str]:
    padding = "=" * (-len(identifier) % 4)
    try:
        raw_value = base64.urlsafe_b64decode((identifier + padding).encode("ascii")).decode("utf-8")
        object_type, object_id, author_id = raw_value.split(LIKE_ID_SEPARATOR)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise Http404("Like not found")
    return object_type, object_id, author_id


class LikeSerializerMixin:
    def _liker_display_name(self, author: Author) -> str:
        for attr in ("display_name", "username", "first_name"):
            value = getattr(author, attr, None)
            if value:
                return value
        return str(author)

    def _serialize_author(self, request, author: Author) -> dict:
        data = AuthorSerializer(author, context={"request": request}).data
        data["apiId"] = data.get("id")
        data["id"] = str(author.id)
        return data

    def _build_entry_like_object(self, request, entry: Entry, liker: Author) -> dict:
        object_url = request.build_absolute_uri(reverse("api:entry-detail", args=[entry.id]))
        like_identifier = encode_like_identifier("entry", str(entry.id), str(liker.id))
        like_id = request.build_absolute_uri(reverse("api:liked-detail", args=[like_identifier]))
        entry_title = getattr(entry, "title", "") or "an entry"
        summary = f"{self._liker_display_name(liker)} likes {entry_title}"
        return {
            "type": "Like",
            "id": like_id,
            "summary": summary,
            "author": self._serialize_author(request, liker),
            "object": object_url,
        }

    def _build_comment_like_object(self, request, comment: Comment, liker: Author) -> dict:
        object_url = request.build_absolute_uri(reverse("api:comment-detail", args=[comment.id]))
        like_identifier = encode_like_identifier("comment", str(comment.id), str(liker.id))
        like_id = request.build_absolute_uri(reverse("api:liked-detail", args=[like_identifier]))
        entry_title = getattr(comment.entry, "title", "")
        target = f"a comment on {entry_title}" if entry_title else "a comment"
        summary = f"{self._liker_display_name(liker)} likes {target}"
        return {
            "type": "Like",
            "id": like_id,
            "summary": summary,
            "author": self._serialize_author(request, liker),
            "object": object_url,
            "published": timezone.now().isoformat(),
        }

    def _retrieve_like_object(self, request, like_identifier: str, expected_author_id: str | None = None) -> dict:
        object_type, object_id, author_id = decode_like_identifier(like_identifier)
        liker = get_object_or_404(Author, id=author_id)
        if expected_author_id is not None and str(liker.id) != str(expected_author_id):
            raise Http404("Like not found")

        if object_type == "entry":
            target = get_object_or_404(Entry, id=object_id)
            if not target.liked_by.filter(id=liker.id).exists():
                raise Http404("Like not found")
            return self._build_entry_like_object(request, target, liker)

        if object_type == "comment":
            target = get_object_or_404(Comment, id=object_id)
            if not target.liked_by.filter(id=liker.id).exists():
                raise Http404("Like not found")
            return self._build_comment_like_object(request, target, liker)

        raise Http404("Like not found")


class PublicEntriesListView(generics.ListAPIView):
    serializer_class = EntrySerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Entry.objects.filter(visibility=Visibility.PUBLIC)
            .select_related("author")
            .order_by("-published")
        )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, int(request.query_params.get("size", 10)))
        start = (page - 1) * size
        end = start + size

        page_qs = queryset[start:end]
        serializer = self.get_serializer(
            page_qs, many=True, context={"request": request}
        )

        return Response(
            {
                "type": "entries",
                "page_number": page,
                "size": size,
                "count": queryset.count(),
                "src": serializer.data,
            }
        )


class EntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/entries/<uuid:entry_id>/
    Returns a single entry if visible to the requester.
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self, entry_id):
        """
        Retrieves the entry object from the database and returns it unless incorrect visibility
        """
        entry = get_object_or_404(Entry, id=entry_id)

        if entry.visibility == "DELETED":
            raise Http404("Entry not found")

        if entry.visibility == Visibility.FRIENDS and (
            not self.request.user.is_authenticated
            or entry.author != self.request.user
            and not entry.author.follow_requests_sent.filter(
                followee=self.request.user, status=FollowRequestStatus.APPROVED
            ).exists()
        ):
            raise Http404("Entry not found")

        return entry

    def get(self, request, entry_id):
        entry = self.get_object(entry_id)
        serializer = EntrySerializer(entry, context={"request": request})
        return Response(serializer.data)
    
def send_comment_to_remote_followers(comment: Comment, request):
    """
    Send a comment object to all remote followers of the entry author,
    respecting visibility (PUBLIC / FRIENDS).
    """
    entry = comment.entry
    author = entry.author
    commenter = comment.author

    current_host = request.build_absolute_uri('/').rstrip('/')

    # Followers of the entry author
    followers_qs = FollowRequest.objects.filter(
        followee=author,
        status=FollowRequestStatus.APPROVED,
    ).select_related("follower")

    # For FRIENDS-only entries we need mutual follow (friends)
    following_ids = set(
        FollowRequest.objects.filter(
            follower=author,
            status=FollowRequestStatus.APPROVED,
        ).values_list("followee_id", flat=True)
    )

    entry_api_url = request.build_absolute_uri(
        reverse("api:entry-detail", args=[entry.id])
    )
    comment_api_url = request.build_absolute_uri(
        reverse("api:comment-detail", args=[comment.id])
    )
    commenter_api_url = request.build_absolute_uri(
        f"/api/authors/{commenter.id}/"
    )

    for fr in followers_qs:
        follower: Author = fr.follower
        is_friend = follower.id in following_ids

        # FRIENDS visibility → only mutuals
        if entry.visibility == Visibility.FRIENDS and not is_friend:
            continue

        host_value = getattr(follower, "host", "") or ""
        follower_host = host_value.rstrip('/')

        # Only send to remote followers
        if not follower_host or follower_host == current_host:
            continue

        # Find RemoteNode config for that host
        remote_node = (
            RemoteNode.objects
            .filter(is_active=True)
            .filter(base_url__startswith=follower_host)
            .first()
        )
        if not remote_node:
            continue

        follower_author_url = f"{follower_host}/api/authors/{follower.id}"
        inbox_url = f"{follower_author_url}/inbox/"

        comment_object = {
            "type": "comment",
            "id": comment_api_url,
            "author": {
                "type": "author",
                "id": commenter_api_url,
                "displayName": getattr(commenter, "display_name", None)
                              or getattr(commenter, "username", ""),
                "host": request.build_absolute_uri("/api/"),
                "github": getattr(commenter, "github", "") or "",
                "profileImage": getattr(commenter, "profile_image", "") or "",
            },
            "comment": comment.content,
            "contentType": comment.content_type or "text/plain",
            "published": (
                comment.created_at.isoformat()
                if comment.created_at else timezone.now().isoformat()
            ),
            "entry": entry_api_url,
        }

        try:
            auth = HTTPBasicAuth(remote_node.username, remote_node.password)
            print(f"[COMMENT→FOLLOWERS] POST -> {inbox_url}")
            resp = requests.post(
                inbox_url,
                json=comment_object,
                auth=auth,
                timeout=10,
            )
            print(f"[COMMENT→FOLLOWERS] <- {resp.status_code} {resp.text[:200]}")
        except requests.RequestException as e:
            print(f"[COMMENT→FOLLOWERS] ERROR sending to {inbox_url}: {e}")
            continue
 
def send_like_to_author_inbox(entry: Entry, liker: Author, request):
    """
    Send a like object to the entry author's inbox if they're on a remote node.
    """
    author = entry.author
    current_host = request.build_absolute_uri('/').rstrip('/')
    author_host = (getattr(author, 'host', '') or '').rstrip('/')
    
    # Only send if author is on a remote node
    if not author_host or author_host == current_host:
        print(f"[LIKE] Author {author.id} is local, not sending to inbox Host = {author_host}")
        return
    
    from entries.models import RemoteNode
    
    # Find the remote node
    remote_node = None
    for node in RemoteNode.objects.filter(is_active=True):
        if author_host.startswith(node.base_url.rstrip('/')):
            remote_node = node
            break
    
    if not remote_node:
        print(f"[LIKE] No remote node configured for host {author_host}")
        return
    
    # Build URLs
    entry_url = request.build_absolute_uri(reverse("api:entry-detail", args=[entry.id]))
    liker_url = request.build_absolute_uri(f"/api/authors/{liker.id}/")
    author_url = f"{author_host}/api/authors/{author.id}"
    inbox_url = f"{author_url}/inbox/"
    
    # Build like object according to spec
    like_object = {
        "type": "Like",
        "summary": f"{getattr(liker, 'display_name', liker.username)} likes your entry",
        "author": {
            "type": "author",
            "id": liker_url,
            "displayName": getattr(liker, 'display_name', None) or liker.username,
            "host": request.build_absolute_uri('/api/'),
            "github": getattr(liker, 'github', ''),
            "profileImage": getattr(liker, 'profile_image', ''),
        },
        "object": entry_url
    }
    
    # Send to remote inbox
    try:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)
        print(f"[LIKE] Sending like to {inbox_url}")
        
        response = requests.post(
            inbox_url,
            json=like_object,
            auth=auth,
            timeout=10
        )
        
        print(f"[LIKE] Response: {response.status_code} - {response.text[:200]}")
        
    except requests.RequestException as e:
        print(f"[LIKE] Error sending like to remote inbox: {e}")

def send_entry_to_remote_followers(entry: Entry, request):
    """
    Send a new/updated entry to remote followers, respecting visibility:

    - PUBLIC  -> all remote followers
    - UNLISTED -> all remote followers
    - FRIENDS -> only remote mutual follows (friends)
    """
    # Don't federate deleted posts
    if entry.visibility == Visibility.DELETED:
        return

    author = entry.author
    current_host = request.build_absolute_uri('/').rstrip('/')

    # All APPROVED followers of this author (local + remote)
    followers_qs = FollowRequest.objects.filter(
        followee=author,
        status=FollowRequestStatus.APPROVED,
    ).select_related('follower')

    # All authors this author is following (for mutual friend check)
    following_ids = set(
        FollowRequest.objects.filter(
            follower=author,
            status=FollowRequestStatus.APPROVED,
        ).values_list('followee_id', flat=True)
    )

    print(f"[send_entry_to_remote_followers] author={author.id} vis={entry.visibility} followers={followers_qs.count()}")

    entry_api_url = request.build_absolute_uri(
        reverse("api:entry-detail", args=[entry.id])
    )
    author_api_url = request.build_absolute_uri(f"/api/authors/{author.id}/")

    for fr in followers_qs:
        follower: Author = fr.follower

        # Determine if this follower is a "friend" (mutual follow)
        is_friend = follower.id in following_ids

        # Visibility-based filtering:
        if entry.visibility == Visibility.FRIENDS and not is_friend:
            # friends-only: skip non-mutuals
            print(f"[send_entry_to_remote_followers] skip {follower.id}: not a friend")
            continue
        # For PUBLIC and UNLISTED: any follower is OK, nothing extra to check

        host_value = getattr(follower, "host", "") or ""
        follower_host = host_value.rstrip('/')

        # Only send to remote followers (host set and not this node)
        if not follower_host or follower_host == current_host:
            print(f"[send_entry_to_remote_followers] skip {follower.id}: local or missing host")
            continue

        follower_author_url = f"{follower_host}/api/authors/{follower.id}"
        inbox_url = f"{follower_author_url}/inbox/"

        remote_node = (
            RemoteNode.objects
            .filter(is_active=True)
            .filter(base_url__startswith=follower_host)
            .first()
        )

        if not remote_node:
            print(f"[send_entry_to_remote_followers] no RemoteNode for host={follower_host}")
            continue

        auth = HTTPBasicAuth(remote_node.username, remote_node.password)

        payload = {
            "type": "entry",
            "id": entry_api_url,
            "title": entry.title,
            "source": entry_api_url,
            "origin": entry_api_url,
            "contentType": entry.content_type,
            "content": entry.content,
            "description": entry.description,
            "visibility": (entry.visibility or "").upper(),
            "published": (entry.published or timezone.now()).isoformat(),
            "author": {
                "type": "author",
                "id": author_api_url,
                "displayName": getattr(author, "display_name", None) or getattr(author, "username", ""),
                "github": getattr(author, "github", "") or "",
                "profileImage": getattr(author, "profile_image", "") or "",
                "host": request.build_absolute_uri('/api/'),
            },
        }

        try:
            print(f"[send_entry_to_remote_followers] POST -> {inbox_url}")
            resp = requests.post(inbox_url, json=payload, auth=auth, timeout=10)
            print(f"[send_entry_to_remote_followers] <- {resp.status_code} {resp.text[:200]}")
        except requests.RequestException as e:
            print(f"[send_entry_to_remote_followers] ERROR sending to {inbox_url}: {e}")
            continue


class MyEntriesListView(generics.ListCreateAPIView):
    """
    GET  [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/
    POST [local]         /api/authors/{AUTHOR_SERIAL}/entries/
    
    Visibility rules:
    - Not authenticated: PUBLIC only
    - Authenticated as author: all entries
    - Authenticated as follower: PUBLIC + UNLISTED
    - Authenticated as friend: all entries
    - Authenticated as remote node: reject (shouldn't happen per spec)
    """
    serializer_class = EntrySerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]  
    

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        author = get_object_or_404(Author, id=author_id)
        
        # Base queryset (exclude deleted)
        base_qs = Entry.objects.filter(author=author).exclude(visibility=Visibility.DELETED)
        
        # Remote node authentication → reject per spec
        if hasattr(self.request.user, 'node'):
            return Response(
                {"detail": "Remote nodes should not pull entries directly"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Not authenticated → PUBLIC only
        if not self.request.user.is_authenticated:
            return base_qs.filter(visibility=Visibility.PUBLIC).order_by('-published')
        
        # Authenticated as the author → all entries
        if str(self.request.user.id) == str(author_id):
            return base_qs.order_by('-published')
        
        # Check follow relationship
        is_follower = FollowRequest.objects.filter(
            follower=self.request.user,
            followee=author,
            status=FollowRequestStatus.APPROVED
        ).exists()
        
        is_followed_back = FollowRequest.objects.filter(
            follower=author,
            followee=self.request.user,
            status=FollowRequestStatus.APPROVED
        ).exists()
        
        is_friend = is_follower and is_followed_back
        
        # Friend → all entries
        if is_friend:
            return base_qs.order_by('-published')
        
        # Follower → PUBLIC + UNLISTED
        if is_follower:
            return base_qs.filter(
                visibility__in=[Visibility.PUBLIC, Visibility.UNLISTED]
            ).order_by('-published')
        
        # Not following → PUBLIC only
        return base_qs.filter(visibility=Visibility.PUBLIC).order_by('-published')

    def list(self, request, *args, **kwargs):
        # Handle remote node rejection in get_queryset
        queryset = self.get_queryset()
        
        # If get_queryset returned a Response (for remote node), return it
        if isinstance(queryset, Response):
            return queryset
        
        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response({"type": "entries", "src": serializer.data})

    def create(self, request, *args, **kwargs):
        author_id = self.kwargs['author_id']
        
        # Must be authenticated as that author
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return Response(
                {"detail": "Must be authenticated as author"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(author=request.user)
        
        # Send to remote followers
        send_entry_to_remote_followers(entry, request)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class AuthorEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    PUT    [local]         /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    DELETE [local]         /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    """
    serializer_class = EntrySerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        author_id = self.kwargs['author_id']
        entry_id = self.kwargs['entry_id']
        
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        
        # Visibility checks
        if entry.visibility == Visibility.DELETED:
            raise Http404("Entry not found")
        
        # For PUT/DELETE: must be authenticated as author
        if self.request.method in ['PUT', 'DELETE']:
            if not self.request.user.is_authenticated or str(self.request.user.id) != str(author_id):
                raise Http404("Entry not found")
        
        # For GET: visibility checks
        elif self.request.method == 'GET':
            if not entry.can_view(self.request.user):
                raise Http404("Entry not found")
        
        return entry

    def perform_update(self, serializer):
        entry = serializer.save()
        send_entry_to_remote_followers(entry, self.request)

    def perform_destroy(self, instance):
        instance.visibility = Visibility.DELETED
        instance.save(update_fields=["visibility"])
        send_entry_to_remote_followers(instance, self.request)

class EntryEditDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / DELETE /api/entries/<uuid:entry_id>/edit/
    Only the author can edit or delete their entry.
    """
    serializer_class = EntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        entry_id = self.kwargs.get("entry_id")
        entry = get_object_or_404(Entry, id=entry_id, author=self.request.user)

        if entry.visibility == "DELETED":
            raise Http404("Entry not found")

        return entry

    def perform_update(self, serializer):
        entry = serializer.save()
        send_entry_to_remote_followers(entry, self.request)

    def perform_destroy(self, instance):
        instance.visibility = "DELETED"
        instance.save(update_fields=["visibility"])
        send_entry_to_remote_followers(instance, self.request)

class EntryLikeView(APIView):
    """
    POST /api/entries/<uuid:entry_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, entry_id):
        entry = get_object_or_404(
            Entry.objects.select_related("author"),
            id=entry_id,
        )

        if entry.visibility == Visibility.DELETED:
            raise Http404("Entry not found")

        if not entry.can_view(request.user):
            if entry.visibility == Visibility.FRIENDS:
                return Response(
                    {"detail": "Not friends with the author."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            raise Http404("Entry not found")

        if entry.visibility == Visibility.FRIENDS and request.user != entry.author:
            is_mutual = FollowRequest.objects.filter(
                follower=request.user,
                followee=entry.author,
                status=FollowRequestStatus.APPROVED,
            ).exists() and FollowRequest.objects.filter(
                follower=entry.author,
                followee=request.user,
                status=FollowRequestStatus.APPROVED,
            ).exists()
            if not is_mutual:
                return Response(
                    {"detail": "Mutual follow required."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Add the like locally
        entry.liked_by.add(request.user)
        likes_count = entry.liked_by.count()
        
        send_like_to_author_inbox(entry, request.user, request)
        
        return Response(
            {"type": "Like", "likes": likes_count},
            status=status.HTTP_200_OK,
        )

class EntryLikesListView(LikeSerializerMixin, APIView):
    """
    GET [local] /api/entries/{ENTRY_ID}/likes
    Returns a paginated list of likes on this entry
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, entry_id):
        entry = get_object_or_404(Entry, id=entry_id)
        if not entry.can_view(request.user):
            raise Http404("Entry not found")

        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, int(request.query_params.get("size", 5)))
        start = (page - 1) * size
        end = start + size

        likes_qs = entry.liked_by.all()
        count = likes_qs.count()
        likes_page = likes_qs[start:end]

        # Use the UUID-based likes endpoint URL
        likes_api_url = request.build_absolute_uri(
            reverse("api:entry-likes", args=[entry.id])
        )

        src = [self._build_entry_like_object(request, entry, author) for author in likes_page]

        return Response({
            "type": "likes",
            "id": likes_api_url,
            "page": page,
            "size": size,
            "count": count,
            "src": src,
        })
    
class EntryLikesFQIDView(LikeSerializerMixin, APIView):
    """
    GET [local] /api/entries/{ENTRY_FQID}/likes
    Returns all likes on this entry (by FQID)
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, entry_fqid):
        # Extract UUID from FQID
        entry_id = entry_fqid.rstrip('/').split('/')[-1]
        entry = get_object_or_404(Entry, id=entry_id)
        
        if not entry.can_view(request.user):
            raise Http404("Entry not found")
        
        likes_qs = entry.liked_by.all()
        src = [self._build_entry_like_object(request, entry, author) for author in likes_qs]
        
        return Response({
            "type": "likes",
            "src": src,
        })

class AuthorEntryLikesListView(LikeSerializerMixin, APIView):
    '''
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes/
    Returns a paginated list of authors who liked the entry.
    '''
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id, entry_id):
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        if not entry.can_view(request.user):
            raise Http404("Entry not found")

        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, int(request.query_params.get("size", 5)))
        start = (page - 1) * size
        end = start + size

        likes_qs = entry.liked_by.all()
        count = likes_qs.count()
        likes_page = likes_qs[start:end]

        likes_api_url = request.build_absolute_uri(
            reverse("api:author-entry-likes", args=[entry.author.id, entry.id])
        )
        entry_html_url = request.build_absolute_uri(reverse("entries:view_entry", args=[entry.id]))

        src = [self._build_entry_like_object(request, entry, author) for author in likes_page]

        return Response(
            {
                "type": "likes",
                "web": entry_html_url,
                "id": likes_api_url,
                "page_number": page,
                "size": size,
                "count": count,
                "src": src,
            }
        )
    
class AuthorEntryCommentsListCreateView(generics.ListCreateAPIView):
    """
    GET  [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments
    POST [local]         /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    _entry = None

    def get_entry(self):
        if self._entry is not None:
            return self._entry
        
        author_id = self.kwargs['author_id']
        entry_id = self.kwargs['entry_id']
        
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        
        if not entry.can_view(self.request.user):
            raise Http404("Entry not found")
        
        self._entry = entry
        return entry

    def get_queryset(self):
        entry = self.get_entry()
        comments = entry.comments.select_related("author")
        
        if (
            entry.visibility == Visibility.FRIENDS
            and self.request.user.is_authenticated
            and self.request.user != entry.author
        ):
            comments = comments.filter(author__in=[self.request.user, entry.author])
        
        return comments.order_by("created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        entry_url = request.build_absolute_uri(
            reverse("api:author-entry-detail", args=[self.kwargs['author_id'], self.kwargs['entry_id']])
        )
        
        return Response({
            "type": "comments",
            "entry": entry_url,
            "comments": serializer.data
        })

    def perform_create(self, serializer):
        entry = self.get_entry()
        
        if not self.request.user.is_authenticated:
            raise Http404("Entry not found")

        comment = serializer.save(entry=entry, author=self.request.user)
        
        # Notify post author if remote
        send_comment_to_author_inbox(comment, self.request)
        
        # Notify remote followers
        send_comment_to_remote_followers(comment, self.request)


class CommentLikesListView(LikeSerializerMixin, APIView):
    '''
    GET /api/entries/<uuid:entry_id>/comments/<uuid:comment_id>/likes/
    Returns a paginated list of authors who liked the comment.
    '''
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id, entry_id, comment_id):
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        if not entry.can_view(request.user):
            raise Http404("Comment not found")
        comment = get_object_or_404(Comment, id=comment_id, entry=entry)

        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, int(request.query_params.get("size", 5)))
        start = (page - 1) * size
        end = start + size

        likes_qs = comment.liked_by.all()
        count = likes_qs.count()
        likes_page = likes_qs[start:end]

        likes_api_url = request.build_absolute_uri(
            reverse(
                "api:author-entry-comment-likes",
                args=[entry.author.id, entry.id, comment.id],
            )
        )
        entry_html_url = request.build_absolute_uri(reverse("entries:view_entry", args=[entry.id]))

        src = [self._build_comment_like_object(request, comment, author) for author in likes_page]

        return Response(
            {
                "type": "likes",
                "web": entry_html_url,
                "id": likes_api_url,
                "page_number": page,
                "size": size,
                "count": count,
                "src": src,
            }
        )

class CommentLikesFQIDView(LikeSerializerMixin, APIView):
    """
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_FQID}/likes
    Returns all likes on a comment (by FQID)
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id, entry_id, comment_fqid):
        # Verify entry belongs to author
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        
        if not entry.can_view(request.user):
            raise Http404("Comment not found")
        
        # Extract comment UUID from FQID
        comment_id = unquote(comment_fqid).rstrip('/').split('/')[-1]
        
        # Get comment
        comment = get_object_or_404(Comment, id=comment_id, entry=entry)
        
        # Get all likes
        likes_qs = comment.liked_by.all()
        src = [self._build_comment_like_object(request, comment, author) for author in likes_qs]
        
        return Response({
            "type": "likes",
            "src": src,
        })

class AuthorLikedListView(LikeSerializerMixin, APIView):
    '''
    GET /api/authors/{AUTHOR_SERIAL}/liked/
    Returns a paginated list of all likes made by the author.
    '''
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_author(self, identifier: str) -> Author:
        return resolve_author_or_404(identifier)

    def get(self, request, author_id):
        liker = self.get_author(str(author_id))
        return self._build_response(request, liker)

    def _build_response(self, request, liker: Author) -> Response:
        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, int(request.query_params.get("size", 10)))
        start = (page - 1) * size
        end = start + size

        entry_likes = (
            Entry.objects.filter(liked_by=liker)
            .select_related("author")
            .order_by("-published")
        )
        comment_likes = (
            Comment.objects.filter(liked_by=liker)
            .select_related("entry", "entry__author")
            .order_by("-created_at")
        )

        items = [self._build_entry_like_object(request, entry, liker) for entry in entry_likes]
        items.extend(
            self._build_comment_like_object(request, comment, liker) for comment in comment_likes
        )

        count = len(items)
        src = items[start:end]

        liked_api_url = request.build_absolute_uri(reverse("api:author-liked", args=[liker.id]))

        return Response(
            {
                "type": "likes",
                "id": liked_api_url,
                "page_number": page,
                "size": size,
                "count": count,
                "src": src,
            }
        )


class AuthorLikedFQIDView(AuthorLikedListView):
    '''
    GET [local] /api/authors/{AUTHOR_FQID}/liked
    Returns a paginated list of all likes made by the author.
    '''
    def get(self, request, author_fqid):
        liker = self.get_author(author_fqid)
        return self._build_response(request, liker)


class AuthorLikedDetailView(LikeSerializerMixin, APIView):
    '''
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}/
    Retrieves a specific like made by the author.
    '''
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id, like_id):
        liker = resolve_author_or_404(str(author_id))
        like_object = self._retrieve_like_object(request, like_id, expected_author_id=liker.id)
        return Response(like_object)

def send_comment_to_author_inbox(comment: Comment, request):
    """
    Send a comment object to the entry author's inbox if they're on a remote node.
    """
    entry = comment.entry
    author = entry.author
    commenter = comment.author
    
    current_host = request.build_absolute_uri('/').rstrip('/')
    author_host = (getattr(author, 'host', '') or '').rstrip('/')
    
    # Only send if author is on a remote node
    if not author_host or author_host == current_host:
        print(f"[COMMENT] Author {author.id} is local, not sending to inbox")
        return
    
    from entries.models import RemoteNode
    
    # Find the remote node
    remote_node = (
        RemoteNode.objects
        .filter(is_active=True)
        .filter(base_url__startswith=author_host)
        .first()
    )
    
    if not remote_node:
        print(f"[COMMENT] No remote node configured for host {author_host}")
        return
    
    # Build URLs
    comment_url = request.build_absolute_uri(reverse("api:comment-detail", args=[comment.id]))
    entry_url = request.build_absolute_uri(reverse("api:entry-detail", args=[entry.id]))
    commenter_url = request.build_absolute_uri(f"/api/authors/{commenter.id}/")
    author_url = f"{author_host}/api/authors/{author.id}"
    inbox_url = f"{author_url}/inbox/"
    
    # Build comment object according to spec
    comment_object = {
        "type": "comment",
        "id": comment_url,
        "author": {
            "type": "author",
            "id": commenter_url,
            "displayName": getattr(commenter, 'display_name', None) or commenter.username,
            "host": request.build_absolute_uri('/api/'),
            "github": getattr(commenter, 'github', ''),
            "profileImage": getattr(commenter, 'profile_image', ''),
        },
        "comment": comment.content,
        "contentType": "text/plain",  
        "published": comment.created_at.isoformat() if comment.created_at else timezone.now().isoformat(),
        "entry": entry_url
    }
    
    # Send to remote inbox
    try:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)
        print(f"[COMMENT] Sending comment to {inbox_url}")
        
        response = requests.post(
            inbox_url,
            json=comment_object,
            auth=auth,
            timeout=10
        )
        
        print(f"[COMMENT] Response: {response.status_code} - {response.text[:200]}")
        
    except requests.RequestException as e:
        print(f"[COMMENT] Error sending comment to remote inbox: {e}")

    
class LikeFQIDView(LikeSerializerMixin, APIView):
    '''
    GET [local] /api/liked/{LIKE_FQID}
    Retrieves a specific like by its fully qualified ID (URL-encoded)
    '''
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, like_fqid):
        decoded_fqid = unquote(like_fqid).rstrip('/')
        
        # Extract the like_id from the FQID
        # FQID format: http://node/api/liked/{LIKE_ID}
        like_id = decoded_fqid.split('/')[-1]
        
        # Use existing logic to retrieve the like
        like_object = self._retrieve_like_object(request, like_id)
        return Response(like_object)
    
class EntryCommentsListCreateView(generics.ListCreateAPIView):
    """
    GET /api/entries/<entry_id>/comments/
    POST /api/entries/<entry_id>/comments/
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    _entry = None

    def get_entry(self):
        if self._entry is not None:
            return self._entry
        entry = get_object_or_404(Entry, id=self.kwargs["entry_id"])
        if not entry.can_view(self.request.user):
            raise Http404("Entry not found")
        self._entry = entry
        return entry

    def get_queryset(self):
        entry = self.get_entry()
        comments = entry.comments.select_related("author")
        if (
            entry.visibility == Visibility.FRIENDS
            and self.request.user.is_authenticated
            and self.request.user != entry.author
        ):
            comments = comments.filter(author__in=[self.request.user, entry.author])
        return comments.order_by("created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(
            queryset, many=True, context=self.get_serializer_context()
        )
        entry_url = request.build_absolute_uri(reverse("api:entry-detail", args=[self.get_entry().id]))
        return Response({"type": "comments", "entry": entry_url, "comments": serializer.data})

    def perform_create(self, serializer):
        entry = self.get_entry()
        if not self.request.user.is_authenticated:
            raise Http404("Entry not found")

        # Save the comment locally once
        comment = serializer.save(entry=entry, author=self.request.user)

        # 1) Notify the *post author* if they are remote
        send_comment_to_author_inbox(comment, self.request)

        # 2) Notify remote followers of this local author (if any)
        send_comment_to_remote_followers(comment, self.request)


        
        # Save the comment locally
        comment = serializer.save(entry=entry, author=self.request.user)
        
        send_comment_to_author_inbox(comment, self.request)

class EntryCommentsFQIDView(generics.ListAPIView):
    """
    GET [local, remote] /api/entries/{ENTRY_FQID}/comments
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        entry_fqid = self.kwargs['entry_fqid']
        entry_id = entry_fqid.rstrip('/').split('/')[-1]
        
        entry = get_object_or_404(Entry, id=entry_id)
        
        if not entry.can_view(self.request.user):
            raise Http404("Entry not found")
        
        return entry.comments.select_related("author").order_by("created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            "type": "comments",
            "comments": serializer.data
        })

class CommentDetailView(generics.RetrieveAPIView):
    """
    GET /api/comments/<comment_id>/
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        comment = get_object_or_404(
            Comment.objects.select_related("entry", "author"),
            id=self.kwargs["comment_id"],
        )
        entry = comment.entry
        if not entry.can_view(self.request.user):
            raise Http404("Comment not found")
        if (
            entry.visibility == Visibility.FRIENDS
            and self.request.user != entry.author
            and self.request.user != comment.author
        ):
            raise Http404("Comment not found")
        return comment
    
class CommentFQIDView(generics.RetrieveAPIView):
    """
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comment/{REMOTE_COMMENT_FQID}
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        entry_id = self.kwargs['entry_id']
        comment_fqid = unquote(self.kwargs['remote_comment_fqid'])
        comment_id = comment_fqid.rstrip('/').split('/')[-1]
        
        comment = get_object_or_404(
            Comment.objects.select_related('entry'),
            id=comment_id,
            entry__id=entry_id
        )
        
        if not comment.entry.can_view(self.request.user):
            raise Http404("Comment not found")
        
        return comment

def send_comment_like_to_author_inbox(comment: Comment, liker: Author, request):
    """
    Send a like object for a comment to the comment author's inbox if they're on a remote node.
    """
    comment_author = comment.author
    current_host = request.build_absolute_uri('/').rstrip('/')
    author_host = (getattr(comment_author, 'host', '') or '').rstrip('/')
    
    # Only send if author is on a remote node
    if not author_host or author_host == current_host:
        return
    
    from entries.models import RemoteNode
    
    remote_node = (
        RemoteNode.objects
        .filter(is_active=True)
        .filter(base_url__startswith=author_host)
        .first()
    )
    
    if not remote_node:
        return
    
    # Build URLs
    comment_url = request.build_absolute_uri(reverse("api:comment-detail", args=[comment.id]))
    liker_url = request.build_absolute_uri(f"/api/authors/{liker.id}/")
    author_url = f"{author_host}/api/authors/{comment_author.id}"
    inbox_url = f"{author_url}/inbox/"
    
    like_object = {
        "type": "Like",
        "summary": f"{getattr(liker, 'display_name', liker.username)} likes your comment",
        "author": {
            "type": "author",
            "id": liker_url,
            "displayName": getattr(liker, 'display_name', None) or liker.username,
            "host": request.build_absolute_uri('/api/'),
            "github": getattr(liker, 'github', ''),
            "profileImage": getattr(liker, 'profile_image', ''),
        },
        "object": comment_url
    }
    
    try:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)
        response = requests.post(inbox_url, json=like_object, auth=auth, timeout=10)
        print(f"[COMMENT_LIKE] Sent to {inbox_url}: {response.status_code}")
    except requests.RequestException as e:
        print(f"[COMMENT_LIKE] Error: {e}")

class CommentLikeView(APIView):
    """
    POST /api/comments/<comment_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(
            Comment.objects.select_related("entry"),
            id=comment_id,
        )
        entry = comment.entry
        if not entry.can_view(request.user):
            raise Http404("Comment not found")
        if (
            entry.visibility == Visibility.FRIENDS
            and request.user not in {entry.author, comment.author}
        ):
            raise Http404("Comment not found")

        comment.liked_by.add(request.user)
        
        send_comment_like_to_author_inbox(comment, request.user, request)
        
        serializer = CommentSerializer(comment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class CommentedListView(generics.ListCreateAPIView):
    """
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/commented
    POST [local] /api/authors/{AUTHOR_SERIAL}/commented
    
    GET: Returns paginated list of comments author has made
    - [local] any entry
    - [remote] public and unlisted entries only
    
    POST: Creates a comment on specified entry and forwards to entry author's inbox
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [IsAuthenticatedNodeOrLocalUser]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        author = get_object_or_404(Author, id=author_id)
        
        # For remote requests: only public + unlisted entries
        if hasattr(self.request.user, 'node'):
            return Comment.objects.filter(
                author=author,
                entry__visibility__in=[Visibility.PUBLIC, Visibility.UNLISTED]
            ).select_related('entry', 'entry__author', 'author').order_by('-created_at')
        
        # For local requests: all comments
        return Comment.objects.filter(
            author=author
        ).select_related('entry', 'entry__author', 'author').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        GET /api/authors/{AUTHOR_SERIAL}/commented
        Returns array of comment objects (spec format)
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Use DRF's built-in pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Return array directly per spec example
            return Response(serializer.data)
        
        # Fallback if pagination is disabled
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        POST /api/authors/{AUTHOR_SERIAL}/commented
        
        Body example:
        {
            "type": "comment",
            "comment": "Great post!",
            "contentType": "text/plain",
            "entry": "http://nodebbbb/api/authors/222/entries/249/"
        }
        
        Creates comment locally and forwards to entry author's inbox
        """
        author_id = self.kwargs['author_id']
        author = get_object_or_404(Author, id=author_id)
        
        # Must be authenticated as that author (local only)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return Response(
                {"detail": "Must be authenticated as this author"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate type field
        if request.data.get('type', '').lower() != 'comment':
            return Response(
                {"detail": "Type must be 'comment'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get entry from comment data
        entry_url = request.data.get('entry', '').rstrip('/')
        if not entry_url:
            return Response(
                {"detail": "Missing 'entry' field"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract entry ID from URL (could be remote or local)
        entry_id = entry_url.split('/')[-1]
        
        try:
            entry = Entry.objects.get(id=entry_id)
        except Entry.DoesNotExist:
            return Response(
                {"detail": "Entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create comment data for serializer
        comment_data = {
            'content': request.data.get('comment', ''),
            'content_type': request.data.get('contentType', 'text/plain'),
        }
        
        # Validate and create comment
        serializer = self.get_serializer(data=comment_data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(entry=entry, author=author)
        
        # Forward to entry author's inbox if remote
        send_comment_to_author_inbox(comment, request)
        
        # Get full serialized response
        response_serializer = self.get_serializer(comment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class CommentedDetailView(generics.RetrieveAPIView):
    """
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}
    Returns single comment object in format
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [IsAuthenticatedNodeOrLocalUser]

    def get_object(self):
        author_id = self.kwargs['author_id']
        comment_id = self.kwargs['comment_id']
        
        comment = get_object_or_404(
            Comment.objects.select_related('entry', 'entry__author', 'author'),
            id=comment_id,
            author__id=author_id
        )
        
        # For remote requests: only public + unlisted entries
        if hasattr(self.request.user, 'node'):
            if comment.entry.visibility not in [Visibility.PUBLIC, Visibility.UNLISTED]:
                raise Http404("Comment not found")
        
        return comment


class CommentedFQIDDetailView(generics.RetrieveAPIView):
    """
    GET [local] /api/commented/{COMMENT_FQID}
    Returns single comment object by FQID
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        comment_fqid = unquote(self.kwargs['comment_fqid'])
        comment_id = comment_fqid.rstrip('/').split('/')[-1]
        
        return get_object_or_404(
            Comment.objects.select_related('entry', 'entry__author', 'author'),
            id=comment_id
        )


class CommentedFQIDListView(generics.ListAPIView):
    """
    GET [local] /api/authors/{AUTHOR_FQID}/commented
    Returns list of comments by author FQID (that local node knows about)
    """
    serializer_class = CommentSerializer
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        author_fqid = unquote(self.kwargs['author_fqid'])
        author_id = author_fqid.rstrip('/').split('/')[-1]
        author = get_object_or_404(Author, id=author_id)
        
        # Local node only knows about comments it has seen
        return Comment.objects.filter(
            author=author
        ).select_related('entry', 'entry__author', 'author').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    
def render_markdown_entry(request, entry_id):
    """
    Renders the Markdown content of an entry into HTML.
    """
    # Fetch the entry with the given ID and ensure it has content_type="text/markdown"
    entry = get_object_or_404(Entry, id=entry_id, content_type="text/markdown")

    # Render the Markdown content to HTML
    parser = commonmark.Parser()
    renderer = commonmark.HtmlRenderer()
    parsed = parser.parse(entry.content)
    rendered_content = renderer.render(parsed)

    # Return the rendered content as JSON
    return JsonResponse({"rendered_content": rendered_content})

class EntryImageView(APIView):
    """
    GET [local, remote] /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image
    Return the binary image if entry is an image type
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id, entry_id):
        entry = get_object_or_404(Entry, id=entry_id, author__id=author_id)
        
        if not entry.can_view(request.user):
            raise Http404("Entry not found")
        
        # Check if it's an image entry
        if not entry.content_type or not entry.content_type.startswith('image/'):
            return Response(
                {"detail": "Entry is not an image"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Decode base64 content
        try:
            # Remove data URL prefix if present
            content = entry.content
            if ';base64,' in content:
                content = content.split(';base64,')[1]
            
            image_data = base64.b64decode(content)
            
            # Determine content type
            mime_type = entry.content_type.split(';')[0]
            
            return HttpResponse(image_data, content_type=mime_type)
        except Exception as e:
            return Response(
                {"detail": f"Error decoding image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EntryImageFQIDView(APIView):
    """
    GET [local, remote] /api/entries/{ENTRY_FQID}/image
    Return the binary image by FQID
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, entry_fqid):
        # Extract UUID from FQID
        entry_id = entry_fqid.rstrip('/').split('/')[-1]
        
        entry = get_object_or_404(Entry, id=entry_id)
        
        if not entry.can_view(request.user):
            raise Http404("Entry not found")
        
        if not entry.content_type or not entry.content_type.startswith('image/'):
            return Response(
                {"detail": "Entry is not an image"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            content = entry.content
            if ';base64,' in content:
                content = content.split(';base64,')[1]
            
            image_data = base64.b64decode(content)
            mime_type = entry.content_type.split(';')[0]
            
            return HttpResponse(image_data, content_type=mime_type)
        except Exception as e:
            return Response(
                {"detail": f"Error decoding image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InboxView(APIView):
    """
    POST /api/authors/{AUTHOR_SERIAL}/inbox/
    Receives posts/entries, likes, comments, and follow requests from remote nodes.
    """
    authentication_classes = [RemoteNodeBasicAuthentication]
    # RemoteNodeBasicAuthentication will 401 bad/unknown/inactive nodes.
    permission_classes = [permissions.AllowAny]

    def post(self, request, author_id):
        # Recipient is the local author who owns this inbox
        try:
            recipient = Author.objects.get(id=author_id)
        except Author.DoesNotExist:
            return Response(
                {"detail": "Author not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data
        obj_type = (data.get("type") or "").lower()

        try:
            if obj_type in ("post", "entry"):
                return self._handle_entry(recipient, data)
            elif obj_type == "like":
                return self._handle_like(recipient, data)
            elif obj_type == "comment":
                return self._handle_comment(recipient, data)
            elif obj_type == "follow":
                return self._handle_follow(recipient, data)
            else:
                return Response(
                    {"detail": f"Unsupported type: {obj_type}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            # Generic safety net – you can tighten this later if needed
            return Response(
                {"detail": f"Error processing {obj_type}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---------- handlers ----------

    def _handle_entry(self, recipient: Author, data: dict):
        """
        Handle incoming post/entry from remote node.
        Spec: type: 'post' (or 'entry' in some examples),
        has 'id', 'title', 'contentType', 'content', 'visibility', 'author' object, etc.
        """
        author_data = data.get("author") or {}
        remote_author = _resolve_remote_author_from_data(author_data)
        if not remote_author:
            return Response(
                {"detail": "Missing or invalid author"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entry_full_id = (data.get("id") or "").rstrip("/")
        if not entry_full_id:
            return Response(
                {"detail": "Missing entry id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract UUID from URL
        parts = [p for p in entry_full_id.split("/") if p]
        entry_uuid = parts[-1]

        # Validate UUID
        import uuid as uuid_module

        try:
            uuid_module.UUID(entry_uuid)
        except ValueError:
            return Response(
                {
                    "detail": (
                        f"Could not extract valid UUID from entry ID: "
                        f"{entry_full_id}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Published timestamp
        published_raw = data.get("published")
        if published_raw:
            try:
                published = date_parser.parse(published_raw)
            except Exception:
                published = timezone.now()
        else:
            published = timezone.now()

        # Map visibility (default PUBLIC)
        visibility_map = {
            "PUBLIC": Visibility.PUBLIC,
            "FRIENDS": Visibility.FRIENDS,
            "UNLISTED": Visibility.UNLISTED,
            "DELETED": Visibility.DELETED,
        }
        visibility = visibility_map.get(
            (data.get("visibility") or "PUBLIC").upper(),
            Visibility.PUBLIC,
        )

        entry, created = Entry.objects.update_or_create(
            id=entry_uuid,
            defaults={
                "author": remote_author,
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "content": data.get("content", ""),
                "content_type": data.get("contentType", "text/plain"),
                "visibility": visibility,
                "published": published,
            },
        )

        return Response(
            {
                "detail": "Entry received",
                "id": str(entry.id),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _handle_like(self, recipient: Author, data: dict):
        """
        Handle incoming like.
        Spec: type: 'like', with
          - author: { ...remote author... }
          - object: URL of entry or comment being liked
        """
        author_data = data.get("author") or {}
        remote_author = _resolve_remote_author_from_data(author_data)
        object_url = (data.get("object") or "").rstrip("/")

        if not remote_author or not object_url:
            return Response(
                {"detail": "Missing author or object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parts = [p for p in object_url.split("/") if p]
        target_id = parts[-1]

        try:
            entry = Entry.objects.get(id=target_id)
            entry.liked_by.add(remote_author)
            return Response(
                {"detail": "Like added to entry"},
                status=status.HTTP_200_OK,
            )
        except Entry.DoesNotExist:
            pass

        try:
            comment = Comment.objects.get(id=target_id)
            comment.liked_by.add(remote_author)
            return Response(
                {"detail": "Like added to comment"},
                status=status.HTTP_200_OK,
            )
        except Comment.DoesNotExist:
            return Response(
                {"detail": "Object not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def _handle_comment(self, recipient: Author, data: dict):
        author_data = data.get("author") or {}
        remote_author = _resolve_remote_author_from_data(author_data)
        entry_url = (data.get("entry") or data.get("object") or "").rstrip("/")
        comment_full_id = (data.get("id") or "").rstrip("/")

        if not remote_author or not entry_url or not comment_full_id:
            return Response(
                {"detail": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Target entry
        parts = [p for p in entry_url.split("/") if p]
        entry_id = parts[-1]

        try:

            entry = Entry.objects.get(id=entry_id)
        except Entry.DoesNotExist:
            return Response(
                {"detail": "Entry not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Extract comment UUID
        comment_id = comment_full_id.split("/")[-1]

        import uuid as uuid_module
        try:
            uuid_module.UUID(comment_id)
        except ValueError:
            return Response(
                {"detail": f"Invalid comment id: {comment_full_id}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment, created = Comment.objects.update_or_create(
            id=comment_id,
            defaults={
                "entry": entry,
                "author": remote_author,
                "content": data.get("comment", ""),
                "content_type": data.get("contentType", "text/plain"),
            },
        )

        return Response(
            {"detail": "Comment received", "id": str(comment.id)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


    def _handle_follow(self, recipient: Author, data: dict):
        """
        Handle incoming follow request.
        """
        print(f"[INBOX FOLLOW] Received data: {data}")
        
        actor_data = data.get("actor") or {}
        print(f"[INBOX FOLLOW] Actor data: {actor_data}")
        
        remote_author = _resolve_remote_author_from_data(actor_data)
        print(f"[INBOX FOLLOW] Resolved remote author: {remote_author}")

        if not remote_author:
            print(f"[INBOX FOLLOW] Failed to resolve remote author!")
            return Response(
                {"detail": "Missing or invalid actor"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print(f"[INBOX FOLLOW] Creating FollowRequest: follower={remote_author.id}, followee={recipient.id}")
        
        fr, created = FollowRequest.objects.get_or_create(
            follower=remote_author,
            followee=recipient,
            defaults={"status": FollowRequestStatus.PENDING},
        )
        
        print(f"[INBOX FOLLOW] FollowRequest created={created}, status={fr.status}")

        return Response(
            {"detail": "Follow request received"},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

class FollowRequestsListView(APIView):
    """
    GET /api/authors/{AUTHOR_SERIAL}/follow_requests
    Returns pending follow requests for the author
    """
    authentication_classes = [HybridAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id):
        author = get_object_or_404(Author, id=author_id)
        
        # Must be that author
        if str(request.user.id) != str(author_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        pending_requests = FollowRequest.objects.filter(
            followee=author,
            status=FollowRequestStatus.PENDING
        ).select_related('follower')
        
        followers = [fr.follower for fr in pending_requests]
        data = AuthorSerializer(followers, many=True, context={'request': request}).data
        
        return Response({
            "type": "follow",
            "requests": data
        })
