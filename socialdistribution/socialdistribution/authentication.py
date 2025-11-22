from rest_framework import authentication
from rest_framework import exceptions
from entries.models import RemoteNode


from rest_framework import authentication
from rest_framework import exceptions
from entries.models import RemoteNode
from django.conf import settings


class RemoteNodeBasicAuthentication(authentication.BasicAuthentication):
    """
    Custom HTTP Basic Authentication for remote nodes.
    Validates credentials against our universal node credentials.
    """

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against our node credentials.
        
        """
        print(f"[AUTH] Incoming auth attempt:")
        print(f"[AUTH] Received userid: {userid}")
        print(f"[AUTH] Received password: {password}")
        print(f"[AUTH] Expected userid: {settings.OUR_NODE_USERNAME}")
        print(f"[AUTH] Expected password: {settings.OUR_NODE_PASSWORD}")
        print(f"[AUTH] Match: {userid == settings.OUR_NODE_USERNAME and password == settings.OUR_NODE_PASSWORD}")
        
        if userid != settings.OUR_NODE_USERNAME or password != settings.OUR_NODE_PASSWORD:
            raise exceptions.AuthenticationFailed('Invalid node credentials')
        
        return (NodeUser(), None)


class NodeUser:
    """
    A simple user-like object to represent an authenticated remote node.
    This allows us to use Django's authentication system with nodes.
    """
    def __init__(self):
        self.username = "remote_node"
        self.is_authenticated = True
        self.is_active = True
        self.pk = "node"
        self.id = "node"

    def __str__(self):
        return "Remote Node"

    @property
    def is_anonymous(self):
        return False

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True