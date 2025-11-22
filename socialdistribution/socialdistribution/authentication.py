from rest_framework import authentication
from rest_framework import exceptions
from entries.models import RemoteNode


class RemoteNodeBasicAuthentication(authentication.BasicAuthentication):
    """
    Custom HTTP Basic Authentication for remote nodes.
    Validates credentials against RemoteNode entries in the database.
    """

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against RemoteNode entries.
        Any active RemoteNode with matching credentials is allowed.
        """
        print(f"[AUTH] Incoming auth attempt:")
        print(f"[AUTH] Received userid: {userid}")
        print(f"[AUTH] Received password: {password}")

        # Look for a RemoteNode with matching credentials
        try:
            node = RemoteNode.objects.get(
                username=userid,
                password=password,
                is_active=True
            )
            print(f"[AUTH] Match found: {node.host}")
            return (NodeUser(node), None)
        except RemoteNode.DoesNotExist:
            print(f"[AUTH] No matching RemoteNode found")
            
            # Log all active nodes for debugging
            print(f"[AUTH] Active RemoteNodes in database:")
            for n in RemoteNode.objects.filter(is_active=True):
                print(f"[AUTH]   - {n.host}: {n.username}:{n.password}")
            
            raise exceptions.AuthenticationFailed('Invalid node credentials')


class NodeUser:
    """
    A simple user-like object to represent an authenticated remote node.
    """

    def __init__(self, node=None):
        self.node = node
        self.username = node.host if node else "remote_node"
        self.is_authenticated = True
        self.is_active = True
        self.pk = node.pk if node else "node"
        self.id = node.pk if node else "node"

    def __str__(self):
        return f"Remote Node: {self.username}"

    @property
    def is_anonymous(self):
        return False

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True