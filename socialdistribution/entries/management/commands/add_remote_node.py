from django.core.management.base import BaseCommand
from entries.models import RemoteNode


class Command(BaseCommand):
    '''Management command to add or update a remote node for HTTP Basic Auth'''
    help = 'Add or update a remote node for HTTP Basic Auth'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Friendly name for the node')
        parser.add_argument('base_url', type=str, help='Base URL of the remote node')
        parser.add_argument('username', type=str, help='Username for authentication')
        parser.add_argument('password', type=str, help='Password for authentication')
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Create the node as inactive',
        )

    def handle(self, *args, **options):
        try:
            # Try to get existing node by base_url
            node = RemoteNode.objects.get(base_url=options['base_url'])
            # Update the existing node
            node.name = options['name']
            node.username = options['username']
            node.password = options['password']
            node.is_active = not options['inactive']
            node.save()
            created = False
            
        except RemoteNode.DoesNotExist:
            # Create a new node
            node = RemoteNode.objects.create(
                name=options['name'],
                base_url=options['base_url'],
                username=options['username'],
                password=options['password'],
                is_active=not options['inactive']
            )
            created = True
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully created remote node: {node.name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully updated remote node: {node.name}')
            )
        
        self.stdout.write(f'  Base URL: {node.base_url}')
        self.stdout.write(f'  Username: {node.username}')
        self.stdout.write(f'  Active: {node.is_active}')