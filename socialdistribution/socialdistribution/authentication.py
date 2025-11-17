from rest_framework import authentication
from rest_framework import exceptions
from entries.models import RemoteNode


class RemoteNodeBasicAuthentication(authentication.BasicAuthentication):
    """
    Custom HTTP Basic Authentication for remote nodes.
    Validates credentials against the RemoteNode model.
    """

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against RemoteNode entries.
        """
        try:
            node = RemoteNode.objects.get(username=userid, is_active=True)
        except RemoteNode.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid node credentials')

        # Check if password matches (plaintext comparison for HTTP Basic Auth)
        if node.password != password:
            raise exceptions.AuthenticationFailed('Invalid node credentials')

        # Return a tuple of (user, auth)
        # We create a NodeUser object to represent the authenticated node
        return (NodeUser(node), node)


class NodeUser:
    """
    A simple user-like object to represent an authenticated remote node.
    This allows us to use Django's authentication system with nodes.
    """
    def __init__(self, node):
        self.node = node
        self.username = node.username
        self.is_authenticated = True
        self.is_active = node.is_active
        self.pk = f"node_{node.pk}"
        self.id = f"node_{node.pk}"

    def __str__(self):
        return f"Node: {self.node.name}"

    @property
    def is_anonymous(self):
        return False

    def has_perm(self, perm, obj=None):
        """Remote nodes have all permissions for now"""
        return True

    def has_module_perms(self, app_label):
        """Remote nodes have all permissions for now"""
        return True