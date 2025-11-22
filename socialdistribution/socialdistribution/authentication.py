from rest_framework import authentication
from rest_framework import exceptions
from entries.models import RemoteNode
from django.conf import settings


class RemoteNodeBasicAuthentication(authentication.BasicAuthentication):
    """
    Custom HTTP Basic Authentication for remote nodes.
    Validates credentials against:
    1. Per-node credentials in RemoteNode database
    2. Universal node credentials from settings (fallback)
    """

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against RemoteNode entries
        OR universal credentials.
        """
        print(f"[AUTH] Incoming auth attempt:")
        print(f"[AUTH] Received userid: {userid}")
        print(f"[AUTH] Received password: {password}")

        # First, try to match against per-node credentials in database
        try:
            node = RemoteNode.objects.get(
                username=userid,
                password=password,
                is_active=True
            )
            print(f"[AUTH] Match found in RemoteNode DB: {node.base_url}")
            return (NodeUser(node), None)
        except RemoteNode.DoesNotExist:
            print(f"[AUTH] No match in RemoteNode DB, trying universal credentials...")

        # Second, try universal credentials from settings
        universal_user = getattr(settings, 'OUR_NODE_USERNAME', None)
        universal_pass = getattr(settings, 'OUR_NODE_PASSWORD', None)
        
        if universal_user and universal_pass:
            print(f"[AUTH] Universal credentials: {universal_user}:{universal_pass}")
            if userid == universal_user and password == universal_pass:
                print(f"[AUTH] Match found using universal credentials!")
                return (NodeUser(None), None)
            else:
                print(f"[AUTH] Universal credentials did not match")
        else:
            print(f"[AUTH] No universal credentials configured in settings")

        # Neither matched - log all options for debugging
        print(f"[AUTH] Authentication FAILED")
        print(f"[AUTH] Active RemoteNodes in database:")
        for n in RemoteNode.objects.filter(is_active=True):
            print(f"[AUTH]   - {n.base_url}: {n.username}:{n.password}")
        
        raise exceptions.AuthenticationFailed('Invalid node credentials')


class NodeUser:
    """
    A simple user-like object to represent an authenticated remote node.
    """

    def __init__(self, node=None):
        self.node = node
        self.username = node.base_url if node else "remote_node"
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