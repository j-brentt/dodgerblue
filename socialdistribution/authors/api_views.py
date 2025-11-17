from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from socialdistribution.permissions import IsAuthenticatedNode, IsAuthenticatedNodeOrLocalUser, IsLocalUserOnly
from django.urls import reverse
import requests
from requests.auth import HTTPBasicAuth
from authors.models import Author, FollowRequest, FollowRequestStatus
from authors.serializers import AuthorSerializer


class AuthorDetailView(generics.RetrieveAPIView):
    """
    GET /api/author/<id>
    Used to retrieve the author details and serialize them
    Accessible to both remote nodes and local users (public data)
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
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
    permission_classes = [permissions.AllowAny]

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
        results = serializer.data
        return Response({
            "type": "authors",
            "count": len(results),
            "results": results,
            "authors": results,
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
                # Use the existing /api/authors/ endpoint on remote nodes
                response = requests.get(
                    f"{node.base_url.rstrip('/')}/api/authors/",
                    auth=HTTPBasicAuth(node.username, node.password) if node.username else None,
                    timeout=5
                )
                
                if response.ok:
                    data = response.json()
                    # Spec says response should have "authors" key
                    authors = data.get('authors', [])
                    
                    # Add node info to each author for display
                    for author in authors:
                        author['_node_name'] = node.name
                        author['_is_remote'] = True
                        # Ensure username exists - extract from displayName if missing
                        if not author.get('username'):
                            display_name = author.get('displayName') or author.get('display_name', 'unknown')
                            author['username'] = display_name.lower().replace(' ', '_')
                    
                    remote_authors.extend(authors)
            except Exception as e:
                # Log but don't fail if one node is down
                print(f"Error fetching from {node.name}: {str(e)}")
                continue
        
        return Response({
            'type': 'authors',
            'local': local_serializer.data,
            'remote': remote_authors,
            'all': local_serializer.data + remote_authors
        })


@api_view(['POST'])
@drf_permission_classes([IsLocalUserOnly])  # Only local users can follow
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
    
    # Handle if they sent just a UUID (from your existing UI)
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
        
        # Build current user's author URL manually (avoid reverse() issues)
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
            return Response(
                {'detail': 'Remote node not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Send to remote inbox
            auth = HTTPBasicAuth(remote_node.username, remote_node.password) if remote_node.username else None

            response = requests.post(
                inbox_url,
                json=follow_request_data,
                auth=auth,
                timeout=10
            )

            if response.ok:
                # Store locally - extract UUID from the remote author URL
                try:
                    # Extract UUID from the target URL
                    remote_uuid = target_author_url.split('/')[-1]
                    import uuid as uuid_module
                    uuid_module.UUID(remote_uuid)  # Validate it's a UUID
                except (ValueError, IndexError):
                    return Response({
                        'detail': 'Invalid remote author UUID',
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Fetch author info from remote node
                try:
                    author_response = requests.get(
                        target_author_url,
                        auth=HTTPBasicAuth(remote_node.username, remote_node.password) if remote_node.username else None,
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
                except:
                    display_name = 'Remote Author'
                    github = ''
                    profile_image = ''
    
                # Store the remote author locally
                remote_author, _ = Author.objects.get_or_create(
                    id=remote_uuid,  # Use just the UUID
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
