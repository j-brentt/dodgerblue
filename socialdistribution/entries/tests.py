from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Entry

User = get_user_model()

class EntryVisibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.author = User.objects.create_user(
            username="alice",
            password="pw",
            display_name="Alice",
        )

        self.public_entry = Entry.objects.create(
            author=self.author,
            title="Public",
            description="",
            content="hello world",
            content_type="text/plain",
            visibility="PUBLIC",
        )

        self.friends_entry = Entry.objects.create(
            author=self.author,
            title="Friends",
            description="",
            content="secret",
            content_type="text/plain",
            visibility="FRIENDS",
        )

    def test_public_entry_visible_to_anonymous(self):
        url = reverse("entries:view_entry", args=[self.public_entry.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_friends_entry_hidden_from_anonymous(self):
        url = reverse("entries:view_entry", args=[self.friends_entry.pk])
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (403, 404))

    def test_author_can_view_own_friends_entry(self):
        self.client.login(username="alice", password="pw")
        url = reverse("entries:view_entry", args=[self.friends_entry.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_stream_shows_author_private_entries(self):
        self.client.login(username="alice", password="pw")
        stream_url = reverse("authors:stream")
        resp = self.client.get(stream_url)
        self.assertContains(resp, "Friends")  # title of the FRIENDS entry