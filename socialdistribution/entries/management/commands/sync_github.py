# entries/management/commands/sync_github.py
from django.core.management.base import BaseCommand
from authors.models import Author
from entries.github_sync import create_github_entries_for_author


class Command(BaseCommand):
    help = "Syncs GitHub activity for authors that have a GitHub URL"

    def handle(self, *args, **options):
        authors = Author.objects.exclude(github__isnull=True).exclude(github__exact="")
        total_entries = 0

        for author in authors:
            count = create_github_entries_for_author(author)
            self.stdout.write(f"{author.display_name}: created {count} entries")
            total_entries += count

        self.stdout.write(self.style.SUCCESS(f"Total entries created: {total_entries}"))
