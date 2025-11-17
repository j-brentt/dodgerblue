from rest_framework import permissions


class IsAuthenticatedNode(permissions.BasePermission):
    """
    Permission class that allows access only to authenticated remote nodes.
    Use this for endpoints that should only be accessible by other nodes.
    """
    message = 'Authentication required for remote node access.'

    def has_permission(self, request, view):
        # Check if authenticated via RemoteNodeBasicAuthentication
        return (
            request.user and 
            hasattr(request.user, 'node') and 
            request.user.is_authenticated
        )


class IsAuthenticatedNodeOrLocalUser(permissions.BasePermission):
    """
    Permission class that allows access to either:
    - Authenticated remote nodes (via HTTP Basic Auth)
    - Local authenticated users (via session auth)
    
    Use this for endpoints that should be accessible by both nodes and local users.
    """
    message = 'Authentication required.'

    def has_permission(self, request, view):
        # Allow if user is authenticated (any type)
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow if it's an authenticated local user
        if not hasattr(request.user, 'node'):
            return True
        
        # Allow if it's an authenticated remote node
        if hasattr(request.user, 'node'):
            return True
        
        return False


class IsLocalUserOnly(permissions.BasePermission):
    """
    Permission class that allows access only to local authenticated users.
    Blocks remote nodes from accessing these endpoints.
    """
    message = 'This endpoint is only accessible by local users.'

    def has_permission(self, request, view):
        # Must be authenticated and NOT be a node
        return (
            request.user and 
            request.user.is_authenticated and 
            not hasattr(request.user, 'node')
        )