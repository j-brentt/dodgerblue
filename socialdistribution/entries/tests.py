from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Entry
from rest_framework.test import APIClient
from rest_framework import status
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

class EntryAPITests(TestCase):
    """
    Test for all entry APIs
    """
    def setUp(self):
        self.client = Client()
        self.author = User.objects.create_user(
            username="alice",
            password="pw",
            display_name="Alice",
        )
        self.author2 = User.objects.create_user(
            username="taco",
            password="pw2",
            display_name="TACO",
        )

        self.public_entry = Entry.objects.create(
            author=self.author,
            title="Public",
            description="",
            content="hello world",
            content_type="text/plain",
            visibility="PUBLIC",
        )
        self.public_entry = Entry.objects.create(
            author=self.author2,
            title="Public",
            description="",
            content="hello world, im taco",
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
        self.deleted_entry = Entry.objects.create(
            author=self.author,
            title="Deleted",
            description="",
            content="something that should be deleted",
            content_type="text/plain",
            visibility="DELETED",
        )

    def test_get_entry(self):
        """
        Test: Get a specific entry with the entry id
        API: GET /api/entries/ <entry id>
        """
         # Make request
        response = self.client.get(f'/api/entries/{self.public_entry.id}/')
        
        # Assert status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_id = f'http://testserver/api/entries/{self.public_entry.id}/'
        # Assert response structure
        self.assertEqual(response.data['type'], 'entry')
        self.assertEqual(response.data['id'], expected_id)
        self.assertEqual(response.data['title'], self.public_entry.title)
        self.assertIn('id', response.data)
        self.assertIn('web', response.data)
    def test_get_deleted_entry_returns_404(self):
        """
        Test: Getting an entry with visibility=DELETED should return 404
        API: GET /api/entries/<entry_id>/
        """
        response = self.client.get(f'/api/entries/{self.deleted_entry.id}/')
        # Expect a 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_friends_entry_returns_404(self):
        """
        Test: Getting an entry with visibility="FRIENDS" should return 404 if current user is not friends with author
        API: GET /api/entries/<entry_id>/
        """
        response = self.client.get(f'/api/entries/{self.friends_entry.id}/')
        # Expect a 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    def test_get_entry_list(self):
        """
        Test: List all public entries
        API: GET api/entries/
        """
        # Make request
        response = self.client.get('/api/entries/')
        
        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify response structure
        self.assertIn('results', response.data)
        
        entries_list = response.data['results']
        
        # Should only contain 2 public entries
        self.assertEqual(len(entries_list), 2)
        
        # Check that all entries have required fields
        for entry in entries_list:
            self.assertEqual(entry['type'], 'entry')
            self.assertIn('id', entry)
            self.assertIn('title', entry)
            self.assertIn('content', entry)
            self.assertIn('content_type', entry)
            self.assertIn('visibility', entry)
            self.assertIn('author', entry)
        
        # Ensure correct titles are in the results
        titles = [e['title'] for e in entries_list]
        self.assertIn('Public', titles)
        self.assertNotIn('Friends', titles)
        self.assertNotIn('Deleted', titles)
    def test_create_entry(self):
        """
        Test: Creating a new entry via POST /api/author/<author_id>/entries/
        """
        self.client.force_login(self.author)  # Authenticate as author

        data = {
            "title": "New Entry",
            "description": "This is a test entry",
            "content": "Hello world from test",
            "content_type": "text/plain",
            "visibility": "PUBLIC"
        }

        response = self.client.post(f'/api/author/{self.author.id}/entries/', data, content_type='application/json')

        # Check that the response is 201 CREATED
        self.assertEqual(response.status_code, 201)

        # Check that the response contains the entry data
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['description'], data['description'])
        self.assertEqual(response.data['content'], data['content'])
        self.assertEqual(response.data['content_type'], data['content_type'])
        self.assertEqual(response.data['visibility'], data['visibility'])

        # Check that the entry exists in the database
        entry_exists = Entry.objects.filter(id=response.data['id'].split('/')[-2]).exists()
        self.assertTrue(entry_exists)
    def test_user_can_view_own_entries(self):
        """
        Test: User should see their own entries including FRIENDS visibility,
        but should not see deleted entries.
        API: GET /api/author/<author_id>/entries/
        """
        # Login as the first author
        self.client.login(username="alice", password="pw")

        # GET request to fetch their entries
        response = self.client.get(f'/api/author/{self.author.id}/entries/')

        self.assertEqual(response.status_code, 200)

        entries_list = response.data.get('src', [])
        self.assertEqual(len(entries_list),2)
        
        titles = [entry['title'] for entry in entries_list]

        # Should contain public and friends entries
        self.assertIn("Public", titles)
        self.assertIn("Friends", titles)

        # Should NOT contain deleted entry
        self.assertNotIn("Deleted", titles)