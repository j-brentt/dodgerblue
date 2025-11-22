from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from socialdistribution.permissions import IsAuthenticatedNode, IsAuthenticatedNodeOrLocalUser, IsLocalUserOnly
from socialdistribution.authentication import RemoteNodeBasicAuthentication  
from django.urls import reverse
import requests
from requests.auth import HTTPBasicAuth
from authors.models import Author, FollowRequest, FollowRequestStatus
from authors.serializers import AuthorSerializer
from django.conf import settings
from urllib.parse import unquote, urlparse
from entries.models import RemoteNode


class AuthorDetailView(generics.RetrieveAPIView):
    """
    GET /api/author/<id>/
    Used to retrieve the author details and serialize them
    Accessible to both remote nodes and local users (public data)
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    # Add authentication for remote nodes
    permission_classes = [permissions.AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        # Log if accessed by remote node
        if hasattr(request.user, 'node'):
            print(f"Remote node {request.user.node.name} accessing author detail")
        
        return super().retrieve(request, *args, **kwargs)


class AuthorListView(generics.ListAPIView):
    """
    GET /api/authors/
    Returns a list of approved public authors.
    Accessible to both remote nodes and local users
    """
    serializer_class = AuthorSerializer
   
    authentication_classes = [RemoteNodeBasicAuthentication]
    permission_classes = [IsAuthenticatedNodeOrLocalUser]  
    pagination_class = None  # Disable pagination for simplicity
    def get_queryset(self):
        return Author.objects.filter(
            is_active=True,
            is_approved=True,
        ).order_by("id")

    def list(self, request, *args, **kwargs):
        # Log if accessed by remote node
        if hasattr(request.user, 'node'):
            print(f"Remote node {request.user.node.name} accessing authors list")
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        authors = serializer.data

        # Spec-compliant shape
        return Response({
            "type": "authors",
            "authors": authors,
        })

class ExploreAuthorsView(APIView):
    """
    GET /api/authors/explore/
    Returns all local authors + authors from connected remote nodes
    Only accessible to local authenticated users (not remote nodes)
    """
    # Only local users should access this endpoint
    permission_classes = [IsLocalUserOnly]
    
    def get(self, request):
        from entries.models import RemoteNode
        
        # Get local authors using existing queryset logic
        local_authors = Author.objects.filter(
            is_active=True,
            is_approved=True,
        ).exclude(id=request.user.id).order_by("id")
        local_serializer = AuthorSerializer(local_authors, many=True, context={'request': request})
        
        # Get remote authors from all connected nodes
        remote_authors = []
        connected_nodes = RemoteNode.objects.filter(is_active=True)
        
        for node in connected_nodes:
            try:
                node_base = node.base_url.rstrip('/')

                response = requests.get(
                    f"{node_base}/api/authors/",
                    auth=HTTPBasicAuth(node.username, node.password),
                    timeout=5
                )
                
                if not response.ok:
                    continue

                data = response.json()
                authors = data.get('authors', [])

                filtered_authors = []
                for author in authors:
                    # Try host first (ActivityPub spec-style), then fall back to id/url
                    host = (author.get('host') or '').rstrip('/')
                    author_id = (author.get('id') or author.get('url') or '').rstrip('/')

                    # Decide if this author is "local" to that node:
                    # 1. If host is present, use it
                    # 2. Otherwise, fall back to id/url
                    source_url = host or author_id
                    if not source_url:
                        continue  # can't determine, skip

                    # Compare by scheme+netloc (so https://test.com and https://test.com/api/... match)
                    parsed_node = urlparse(node_base)
                    parsed_source = urlparse(source_url)

                    same_origin = (
                        parsed_node.scheme == parsed_source.scheme and
                        parsed_node.netloc == parsed_source.netloc
                    )
                    if not same_origin:
                        # This is a "remote of a remote" – skip it
                        continue

                    # At this point we've confirmed the author belongs to this node
                    author['_node_name'] = node.name
                    author['_is_remote'] = True

                    # Ensure username exists - extract from displayName if missing
                    if not author.get('username'):
                        display_name = (
                            author.get('displayName')
                            or author.get('display_name')
                            or 'unknown'
                        )
                        author['username'] = display_name.lower().replace(' ', '_')

                    filtered_authors.append(author)

                remote_authors.extend(filtered_authors)

            except Exception as e:
                # Log but don't fail if one node is down or misbehaving
                print(f"Error fetching from {node.name}: {str(e)}")
                continue
        
        return Response({
            'type': 'authors',
            'local': local_serializer.data,
            'remote': remote_authors,
            'all': local_serializer.data + remote_authors
        })


@api_view(['POST'])
@drf_permission_classes([IsLocalUserOnly])
def api_follow_author(request):
    """
    POST /api/authors/follow/
    API endpoint for following local or remote authors
    Body: { "author_id": "full URL of author to follow" }
    Only accessible to local authenticated users
    """
    target_author_url = request.data.get('author_id', '').rstrip('/')
    
    if not target_author_url:
        return Response(
            {'detail': 'author_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if it's a local follow (just the UUID) or remote (full URL)
    current_host = request.build_absolute_uri('/').rstrip('/')
    
    # Handle if they sent just a UUID
    if not target_author_url.startswith('http'):
        # Local author by UUID
        try:
            target_author = Author.objects.get(id=target_author_url)
            
            follow_req, created = FollowRequest.objects.get_or_create(
                follower=request.user,
                followee=target_author,
                defaults={'status': FollowRequestStatus.PENDING}
            )
            
            return Response({
                'detail': 'Follow request sent',
                'created': created
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Author.DoesNotExist:
            return Response(
                {'detail': 'Author not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # It's a full URL - check if local or remote
    if target_author_url.startswith(current_host):
        # LOCAL but with full URL
        try:
            target_author_id = target_author_url.split('/')[-1]
            target_author = Author.objects.get(id=target_author_id)
            
            follow_req, created = FollowRequest.objects.get_or_create(
                follower=request.user,
                followee=target_author,
                defaults={'status': FollowRequestStatus.PENDING}
            )
            
            return Response({
                'detail': 'Follow request sent (local)',
                'created': created
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Author.DoesNotExist:
            return Response(
                {'detail': 'Author not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    else:
        # REMOTE AUTHOR - send to their inbox
        from entries.models import RemoteNode
        
        print(f"[FOLLOW] Following remote author: {target_author_url}")
        
        # Build current user's author URL
        current_user_url = request.build_absolute_uri(f'/api/authors/{request.user.id}/')
        
        actor_data = {
            'type': 'author',
            'id': current_user_url,
            'displayName': getattr(request.user, 'display_name', None) or request.user.username,
            'host': request.build_absolute_uri('/api/'),
            'github': getattr(request.user, 'github', ''),
            'profileImage': getattr(request.user, 'profile_image', ''),
        }
        
        follow_request_data = {
            'type': 'follow',
            'summary': f"{actor_data['displayName']} wants to follow you",
            'actor': actor_data,
            'object': {
                'type': 'author',
                'id': target_author_url,
            }
        }
        
        # Find the remote node
        inbox_url = f"{target_author_url}/inbox/"
        
        remote_node = None
        for node in RemoteNode.objects.filter(is_active=True):
            if target_author_url.startswith(node.base_url.rstrip('/')):
                remote_node = node
                break
        
        if not remote_node:
            print(f"[FOLLOW] No remote node configured for {target_author_url}")
            return Response(
                {'detail': 'Remote node not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            
            auth = HTTPBasicAuth(remote_node.username, remote_node.password)
            
            print(f"[FOLLOW] POSTing to {inbox_url}")
            print(f"[FOLLOW] Payload: {follow_request_data}")
            response = requests.post(
                inbox_url,
                json=follow_request_data,
                auth=auth,
                timeout=10
            )
            
            print(f"[FOLLOW] Response: {response.status_code} - {response.text[:200]}")

            if response.ok:
                # Extract UUID from the remote author URL
                try:
                    remote_uuid = target_author_url.split('/')[-1]
                    import uuid as uuid_module
                    uuid_module.UUID(remote_uuid)
                except (ValueError, IndexError):
                    return Response({
                        'detail': 'Invalid remote author UUID',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    author_response = requests.get(
                        target_author_url,
                        auth=HTTPBasicAuth(remote_node.username, remote_node.password),
                        timeout=5
                    )
                    if author_response.ok:
                        author_info = author_response.json()
                        display_name = author_info.get('displayName', 'Remote Author')
                        github = author_info.get('github', '')
                        profile_image = author_info.get('profileImage', '')
                    else:
                        display_name = 'Remote Author'
                        github = ''
                        profile_image = ''
                except Exception as e:
                    print(f"[FOLLOW] Error fetching author info: {e}")
                    display_name = 'Remote Author'
                    github = ''
                    profile_image = ''
    
                # Store the remote author locally
                remote_author, _ = Author.objects.get_or_create(
                    id=remote_uuid,
                    defaults={
                        'username': f"remote_{remote_uuid[:20]}",
                        'display_name': display_name,
                        'github': github,
                        'profile_image': profile_image,
                        'is_active': False,
                    }
                )

                # Treat remote follow as already accepted on *our* node
                follow_req, created = FollowRequest.objects.get_or_create(
                    follower=request.user,
                    followee=remote_author,
                    defaults={'status': FollowRequestStatus.APPROVED},
                )

                if not created and follow_req.status != FollowRequestStatus.APPROVED:
                    follow_req.status = FollowRequestStatus.APPROVED
                    follow_req.save()

                return Response({
                    'detail': 'Now following remote author',
                    'created': created
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

            else:
                return Response({
                    'detail': 'Failed to send to remote node',
                    'remote_status': response.status_code,
                    'remote_response': response.text[:200]
                }, status=status.HTTP_502_BAD_GATEWAY)
        
        except requests.exceptions.RequestException as e:
            import traceback
            traceback.print_exc()
            return Response({
                'detail': f'Connection error: {str(e)}'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
@api_view(['GET'])
@drf_permission_classes([IsLocalUserOnly])
def check_follow_status(request, author_id):
    """
    GET /api/authors/<uuid:author_id>/follow-status/
    Check if the current user follows this author.
    For REMOTE authors, never return 'pending' – from our node's POV it's
    either 'following' (have a FollowRequest row) or 'not_following'.
    """
    try:
        target_author = Author.objects.get(id=author_id)
    except Author.DoesNotExist:
        return Response({'status': 'not_following'}, status=status.HTTP_200_OK)

    follow_req = FollowRequest.objects.filter(
        follower=request.user,
        followee=target_author
    ).first()

    # Figure out if this author is remote
    current_host = request.build_absolute_uri('/').rstrip('/')
    author_host = (getattr(target_author, 'host', '') or '').rstrip('/')

    is_remote = bool(author_host and author_host != current_host)

    if not follow_req:
        status_value = 'not_following'
    else:
        if is_remote:
            # For remote authors: if we have a FollowRequest row at all,
            # treat as "following" (per spec: just show them as followed).
            if follow_req.status == FollowRequestStatus.PENDING:
                # Upgrade old data if it was left as pending
                follow_req.status = FollowRequestStatus.APPROVED
                follow_req.save(update_fields=['status'])
            status_value = 'following'
        else:
            # Local authors keep the normal pending/approved semantics
            if follow_req.status == FollowRequestStatus.APPROVED:
                status_value = 'following'
            elif follow_req.status == FollowRequestStatus.PENDING:
                status_value = 'pending'
            else:
                status_value = 'not_following'

    return Response({'status': status_value})


@api_view(['POST'])
@drf_permission_classes([IsLocalUserOnly])
def api_unfollow_author(request, author_id):
    """
    POST /api/authors/<uuid:author_id>/unfollow/
    Unfollow an author (local or remote)
    """
    try:
        target_author = Author.objects.get(id=author_id)
    except Author.DoesNotExist:
        return Response(
            {'detail': 'Author not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    follow_req = FollowRequest.objects.filter(
        follower=request.user,
        followee=target_author
    ).first()
    
    if follow_req:
        follow_req.delete()
        return Response({'detail': 'Unfollowed successfully'}, status=status.HTTP_200_OK)
    
    return Response({'detail': 'You are not following this author'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@drf_permission_classes([IsLocalUserOnly])
def followers_list_api(request, author_id):
    """
    GET /api/authors/{AUTHOR_SERIAL}/followers
    Example in spec.

    Local-only: must be authenticated as AUTHOR_SERIAL.
    Response:
    {
        "type": "followers",
        "followers": [ <author objects> ]
    }
    """
    try:
        local_author = Author.objects.get(id=author_id)
    except Author.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Local only: must be that author
    if str(request.user.id) != str(author_id):
        return Response(status=status.HTTP_403_FORBIDDEN)

    follow_qs = FollowRequest.objects.filter(
        followee=local_author,
        status=FollowRequestStatus.APPROVED,
    ).select_related("follower")

    followers = [fr.follower for fr in follow_qs]
    data = AuthorSerializer(followers, many=True, context={'request': request}).data

    return Response({
        "type": "followers",
        "followers": data,
    }, status=status.HTTP_200_OK)

@api_view(['GET', 'PUT', 'DELETE'])
@drf_permission_classes([IsAuthenticatedNodeOrLocalUser])
def followers_detail_api(request, author_id, foreign_author_fqid):
    """
    /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}

    GET  [local, remote]: check if FOREIGN_AUTHOR_FQID is a follower of AUTHOR_SERIAL
                          -> 200 with author if follower, 404 otherwise
    PUT  [local]:         accept FOREIGN_AUTHOR_FQID as follower (must have PENDING FollowRequest)
                          -> 404 if no matching pending follow request
    DELETE [local]:       deny/remove FOREIGN_AUTHOR_FQID
                          -> 404 if no matching follow request or follower
    """

    try:
        local_author = Author.objects.get(id=author_id)
    except Author.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    foreign_fqid = unquote(foreign_author_fqid).rstrip('/')

    # Helper: map FQID -> Author (local or shadow-remote)
    def get_or_create_foreign_author():
        if not foreign_fqid:
            return None

        # bare UUID / local serial handling (not strictly spec, but convenient)
        if not foreign_fqid.startswith('http'):
            try:
                return Author.objects.get(id=foreign_fqid)
            except Author.DoesNotExist:
                return None

        current_api_root = request.build_absolute_uri('/api/').rstrip('/')

        # Local full API URL
        if foreign_fqid.startswith(current_api_root):
            foreign_id = foreign_fqid.rstrip('/').split('/')[-1]
            try:
                return Author.objects.get(id=foreign_id)
            except Author.DoesNotExist:
                return None

        # Remote FQID: http://remote/api/authors/{UUID}
        remote_serial = foreign_fqid.rstrip('/').split('/')[-1]
        try:
            import uuid as uuid_module
            uuid_module.UUID(remote_serial)
        except (ValueError, IndexError):
            return None

        display_name = 'Remote Author'
        github = ''
        profile_image = ''
        try:
            remote_node = None
            for node in RemoteNode.objects.filter(is_active=True):
                if foreign_fqid.startswith(node.base_url.rstrip('/')):
                    remote_node = node
                    break

            if remote_node:
                resp = requests.get(
                    foreign_fqid,
                    auth=HTTPBasicAuth(remote_node.username, remote_node.password),
                    timeout=5,
                )
                if resp.ok:
                    info = resp.json()
                    display_name = info.get('displayName', display_name)
                    github = info.get('github', github)
                    profile_image = info.get('profileImage', profile_image)
        except Exception as e:
            print(f"[FOLLOWERS API] error fetching remote author info: {e}")

        # Derive host from FQID up to /api/
        host = None
        idx = foreign_fqid.find('/api/')
        if idx != -1:
            host = foreign_fqid[:idx+5]  # include '/api/'

        foreign_author, _ = Author.objects.get_or_create(
            id=remote_serial,
            defaults={
                "username": f"remote_{remote_serial[:20]}",
                "display_name": display_name,
                "github": github,
                "profile_image": profile_image,
                "host": host,
                "is_active": False,
            },
        )
        return foreign_author

    foreign_author = get_or_create_foreign_author()

    is_remote_request = hasattr(request.user, 'node')

    # Remote node is only allowed GET, not PUT/DELETE
    if is_remote_request and request.method in ['PUT', 'DELETE']:
        return Response(status=status.HTTP_403_FORBIDDEN)

    # Local requests must act as that author
    if not is_remote_request and str(request.user.id) != str(author_id):
        return Response(status=status.HTTP_403_FORBIDDEN)

    # For GET/DELETE we need a resolvable Author
    if request.method in ['GET', 'DELETE'] and not foreign_author:
        return Response(status=status.HTTP_404_NOT_FOUND)

    follow_req = None
    if foreign_author:
        follow_req = FollowRequest.objects.filter(
            follower=foreign_author,
            followee=local_author,
        ).first()

    # ---------- GET: check if follower ----------
    if request.method == 'GET':
        # Only APPROVED counts as follower; anything else -> 404
        if not follow_req or follow_req.status != FollowRequestStatus.APPROVED:
            return Response(status=status.HTTP_404_NOT_FOUND)

        data = AuthorSerializer(foreign_author, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)

    # ---------- PUT: accept follower (local only) ----------
    if request.method == 'PUT':
        # Must have a PENDING request to accept, otherwise 404 per spec
        if not follow_req or follow_req.status != FollowRequestStatus.PENDING:
            return Response(status=status.HTTP_404_NOT_FOUND)

        follow_req.approve()
        data = AuthorSerializer(foreign_author, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)

    # ---------- DELETE: deny / remove follower ----------
    if request.method == 'DELETE':
        # Must return 404 if there is no matching follow request or follower
        if not follow_req:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Deny / revoke by marking REJECTED
        follow_req.reject()
        return Response(status=status.HTTP_204_NO_CONTENT)
