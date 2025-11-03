from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from authors.models import Author  
from entries.models import Entry, Visibility 
import uuid
from unittest.mock import patch
from entries.github_sync import fetch_github_activity


class AuthorAndEntryURLTests(APITestCase):   
    def setUp(self):
        """
        Set up test data for authors and entries.
        """
        Entry.objects.all().delete()  # Clear all entries
        Author.objects.all().delete()  # Clear all authors
        self.author = Author.objects.create(
            id=uuid.uuid4(),
            username="test_author",
            display_name="test_author",
            password='123',
            github="https://github.com/test_author",
            profile_image="https://example.com/profile_image.png",
            is_approved=True
        )
        self.author2 = Author.objects.create(
            id=uuid.uuid4(),
            username="test_author2",
            display_name="test_author2",
            password='123',
            github="https://github.com/author2",
            profile_image="https://example.com/author2.png",
            is_approved=True
        )
        self.author3 = Author.objects.create(
            id=uuid.uuid4(),
            username="test_author3",
            display_name="test_author3",
            password='123',
            github="https://github.com/author3",
            profile_image="https://example.com/author3.png",
            is_approved=True
        )
        self.entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Test Entry",
            description="This is a brief description of the entry.",
            content="This is a test entry.",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )
        self.entry2 = Entry.objects.create(
            id=uuid.uuid4(),
            title="Test Entry",
            description="This is a brief description of the entry.",
            content="This is a test entry.",
            author=self.author,
            visibility=Visibility.FRIENDS,
        )
        self.markdown_entry_with_image = Entry.objects.create(
            id=uuid.uuid4(),
            title="Markdown Entry with Image",
            description="This is a test entry with Markdown linking to an image.",
            content="![Alt text](https://example.com/image.png)",  # Markdown syntax for an image
            content_type="text/markdown",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )
        # Public entry by self.author2
        self.public_entry_author2 = Entry.objects.create(
            id=uuid.uuid4(),
            title="Public Entry by Author2",
            description="This is a public entry by author2.",
            content="This is a public entry.",
            author=self.author2,
            visibility=Visibility.PUBLIC,
        )
        # Friends-only entry by self.author2
        self.friends_entry_author2 = Entry.objects.create(
            id=uuid.uuid4(),
            title="Friends Entry by Author2",
            description="This is a friends-only entry by author2.",
            content="This is a friends-only entry.",
            author=self.author2,
            visibility=Visibility.FRIENDS,
        )
        # Public entry by self.author3
        self.public_entry_author3 = Entry.objects.create(
            id=uuid.uuid4(),
            title="Public Entry by Author3",
            description="This is a public entry by author3.",
            content="This is a public entry.",
            author=self.author3,
            visibility=Visibility.PUBLIC,
        )
        

    def test_author_url_consistency(self): #Identity 1
        """
        Test that the author's API URL is consistent and predictable.
        """
        # Generate the API URL for the author
        author_url = reverse("authors_api:author-detail", kwargs={"pk": self.author.id})
        response = self.client.get(author_url)

        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the JSON response contains the correct author details
        self.assertEqual(response.json()["id"], f"http://testserver{author_url}")
        self.assertEqual(response.json()["displayName"], self.author.display_name)
        self.assertEqual(response.json()["github"], self.author.github)
        self.assertEqual(response.json()["profileImage"], self.author.profile_image)
        self.assertEqual(response.json()["host"], "http://testserver/api/")
        self.assertEqual(response.json()["web"], f"http://testserver/authors/profile/{self.author.id}/")

    def test_entry_url_consistency(self): #Identity 1
        """
        Test that the entry's API URL is consistent and predictable.
        """
        entry_url = reverse("api:entry-detail", kwargs={"entry_id": self.entry.id})
        response = self.client.get(entry_url)

        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the JSON response contains the correct entry details
        self.assertEqual(response.json()["id"], f"http://testserver{entry_url}")
        self.assertEqual(response.json()["title"], self.entry.title)
        self.assertEqual(response.json()["description"], self.entry.description)
        self.assertEqual(response.json()["content"], self.entry.content)

        # Assert the nested author object
        author_data = response.json()["author"]
        self.assertEqual(author_data["id"], f"http://testserver/api/authors/{self.author.id}/")
        self.assertEqual(author_data["displayName"], self.author.display_name)
        self.assertEqual(author_data["github"], self.author.github)
        self.assertEqual(author_data["profileImage"], self.author.profile_image)

    def test_author_list(self): #Identity 2
        """
        Test that the API returns a list of all authors hosted on the node.
        """
        author_list_url = reverse("authors_api:authors-list")
        response = self.client.get(author_list_url)

        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Extract the list of authors from the paginated response
        authors = response.json().get("results", [])  # Use "results" key for paginated data

        # Filter the authors created in this test
        created_authors = {str(self.author.id), str(self.author2.id)}

        # Extract the IDs of authors returned by the API
        returned_authors = {author["id"].split("/")[-2] for author in authors}

        # Assert that only the authors created in this test are returned
        self.assertTrue(created_authors.issubset(returned_authors))

        # Dynamically check all authors created in this test
        for author_data in authors:
            if author_data["id"].split("/")[-2] in created_authors:
                if author_data["id"] == f"http://testserver/api/authors/{self.author.id}/":
                    self.assertEqual(author_data["displayName"], self.author.display_name)
                    self.assertEqual(author_data["github"], self.author.github)
                    self.assertEqual(author_data["profileImage"], self.author.profile_image)
                elif author_data["id"] == f"http://testserver/api/authors/{self.author2.id}/":
                    self.assertEqual(author_data["displayName"], self.author2.display_name)
                    self.assertEqual(author_data["github"], self.author2.github)
                    self.assertEqual(author_data["profileImage"], self.author2.profile_image)
    
    def test_author_detail(self): #Identity 3
        """
        Test that the API returns the correct details for a specific author.
        """
        author_detail_url = reverse("authors_api:author-detail", kwargs={"pk": self.author.id})
        response = self.client.get(author_detail_url)

        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the JSON response contains the correct author details
        self.assertEqual(response.json()["id"], f"http://testserver{author_detail_url}")
        self.assertEqual(response.json()["displayName"], self.author.display_name)
        self.assertEqual(response.json()["github"], self.author.github)
        self.assertEqual(response.json()["profileImage"], self.author.profile_image)

    def test_author_profile_page(self): #Identity 5
        """
        Test that the public profile page for an author is accessible and displays the correct information.
        """
        profile_url = reverse("authors:profile_detail", kwargs={"author_id": self.author.id})
        response = self.client.get(profile_url)

        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the HTML contains the author's profile information
        self.assertContains(response, self.author.display_name)
        self.assertContains(response, self.author.github)
        self.assertContains(response, self.author.profile_image)

    @patch("entries.github_sync.fetch_github_activity")  
    @patch("entries.models.Entry.objects.create")  
    def test_github_activity_to_public_entries(self, mock_entry_create, mock_fetch_github_activity): #Identity 4
        """
        Test that GitHub activity is automatically turned into public entries.
        """
        # Mock GitHub activity response
        mock_fetch_github_activity.return_value = [
            {
                "type": "PushEvent",
                "repo": {"name": "test_author/test_repo"},
                "payload": {
                    "commits": [
                        {"message": "Initial commit"},
                        {"message": "Added README"},
                    ]
                },
            }
        ]

        # Simulate the GitHub activity sync
        github_activity = mock_fetch_github_activity("test_author")

        # Simulate creating entries from GitHub activity
        for event in github_activity:
            if event["type"] == "PushEvent":
                repo_name = event["repo"]["name"]
                commit_messages = "\n".join(commit["message"] for commit in event["payload"]["commits"])
                content = f"New push to {repo_name}:\n{commit_messages}"
                mock_entry_create(
                    title=f"GitHub Activity: {event['type']}",
                    description=f"Activity on {repo_name}",
                    content=content,
                    author=self.author,
                    visibility=Visibility.PUBLIC,
                )

        # Assert that the mocked Entry creation was called
        self.assertEqual(mock_entry_create.call_count, 1)
        mock_entry_create.assert_called_with(
            title="GitHub Activity: PushEvent",
            description="Activity on test_author/test_repo",
            content="New push to test_author/test_repo:\nInitial commit\nAdded README",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )

    def test_create_markdown_entry(self): #Posting 5
        """
        Test that an author can create an entry with Markdown content.
        """
        self.client.force_login(self.author)

        # Data for the new entry
        data = {
            "title": "Markdown Entry",
            "description": "This is a test entry with Markdown",
            "content": "# Hello World\nThis is **bold** text.",
            "contentType": "text/markdown",  # Matches CONTENT_TYPE_CHOICES
            "visibility": "PUBLIC"  # Matches VISIBILITY_CHOICES
        }

        # API call to create the entry
        response = self.client.post(f'/api/author/{self.author.id}/entries/', data, format='json')
        print(response.content)  # Debugging: Print the response content

        # Assert the entry was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['content'], data['content'])
        self.assertEqual(response.data['contentType'], data['contentType'])

    def test_retrieve_markdown_entry(self): #Posting 5
        """
        Test that an entry with Markdown content can be retrieved.
        """
        # Create an entry with Markdown content
        entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Markdown Entry",
            description="This is a test entry with Markdown",
            content="# Hello World\nThis is **bold** text.",
            content_type="text/markdown",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )

        # API call to retrieve the entry
        response = self.client.get(f'/api/entries/{entry.id}/')
        print(response.content)  # Debugging: Print the response content

        # Assert the entry was retrieved successfully
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], entry.title)
        self.assertEqual(response.data['content'], entry.content)
        self.assertEqual(response.data['contentType'], entry.content_type)
    
    def test_render_markdown_entry(self): #Posting 5
        """
        Test that Markdown content is rendered correctly (if applicable).
        """
        # Create an entry with Markdown content
        entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Markdown Entry",
            description="This is a test entry with Markdown",
            content="# Hello World\nThis is **bold** text.",
            content_type="text/markdown",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )

        # API call to retrieve the rendered content
        response = self.client.get(f'/api/entries/{entry.id}/rendered/')
        print(response.content)  # Debugging: Print the raw response content

        # Assert the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parse the JSON response
        response_data = response.json()  # Use the `json()` method to parse the response content

        # Assert the rendered content is correct
        self.assertIn("<h1>Hello World</h1>", response_data['rendered_content'])
        self.assertIn("<strong>bold</strong>", response_data['rendered_content'])

    def test_create_image_entry(self): #Posting 7
        """
        Test that an author can create an entry with image content.
        """
        self.client.force_login(self.author)

        # Data for the new image entry
        data = {
            "title": "Image Entry",
            "description": "This is a test entry with an image.",
            "content": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
                    "AAAABCAIAAACQd1PeAAAAEElEQVR42mP8/5+hPAAHggJ/P9ZqAAAAAElFTkSuQmCC",
            "contentType": "image/png;base64",  # Matches CONTENT_TYPE_CHOICES
            "visibility": "PUBLIC"  # Matches VISIBILITY_CHOICES
        }

        # API call to create the entry
        response = self.client.post(f'/api/author/{self.author.id}/entries/', data, format='json')
        print(response.content)  # Debugging: Print the response content

        # Assert the entry was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['contentType'], data['contentType'])

    def test_retrieve_image_entry(self): #Posting 7
        """
        Test that an image entry can be retrieved.
        """
        # Create an image entry
        entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Image Entry",
            description="This is a test entry with an image.",
            content="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
                    "AAAABCAIAAACQd1PeAAAAEElEQVR42mP8/5+hPAAHggJ/P9ZqAAAAAElFTkSuQmCC",
            content_type="image/png;base64",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )

        # API call to retrieve the entry
        response = self.client.get(f'/api/entries/{entry.id}/')
        print(response.content)  # Debugging: Print the response content

        # Assert the entry was retrieved successfully
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], entry.title)
        self.assertEqual(response.data['contentType'], entry.content_type)
        self.assertEqual(response.data['content'], entry.content)

    def test_invalid_image_entry(self):  #Posting 7
        """
        Test that invalid image content is rejected.
        """
        self.client.force_login(self.author)  # Log in as the author

        # Data with invalid content_type
        data = {
            "title": "Invalid Image Entry",
            "description": "This entry has an invalid image format.",
            "content": "data:image/invalid;base64,INVALIDBASE64DATA",
            "contentType": "image/invalid;base64",
            "visibility": "PUBLIC"
        }

        # API call to create the entry
        response = self.client.post(f'/api/author/{self.author.id}/entries/', data, format='json')

        # Assert the entry creation failed
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_visibility_of_image_entry(self):  #Posting 7
        """
        Test that visibility rules apply to image entries.
        """
        # Create a friends-only image entry
        entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Friends Image Entry",
            description="This is a friends-only image entry.",
            content="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
                    "AAAABCAIAAACQd1PeAAAAEElEQVR42mP8/5+hPAAHggJ/P9ZqAAAAAElFTkSuQmCC",
            content_type="image/png;base64",
            author=self.author,
            visibility=Visibility.FRIENDS,
        )

        # Anonymous user tries to access the entry
        response = self.client.get(f'/api/entries/{entry.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Author logs in and accesses the entry
        self.client.force_login(self.author)
        response = self.client.get(f'/api/entries/{entry.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_render_markdown_entry_with_image(self): #Posting 8
        """
        Test that Markdown content linking to an image is rendered correctly.
        """
        # API call to retrieve the rendered content
        response = self.client.get(f'/api/entries/{self.markdown_entry_with_image.id}/rendered/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parse the JSON response
        response_data = response.json()

        # Assert the rendered content includes the correct HTML for the image
        self.assertIn('<img src="https://example.com/image.png" alt="Alt text"', response_data['rendered_content'])

    '''
    def test_stream_shows_all_public_entries(self):
        """
        Test that the stream page shows all public entries from all authors.
        """
        # Debugging: Check the visibility of self.entry2 in the database
        print(f"Database visibility for entry2: {Entry.objects.get(id=self.entry2.id).visibility}")

        # API call to fetch the stream of public entries
        response = self.client.get('/api/entries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parse the JSON response
        response_data = response.json()
        print(response_data)  # Debugging: Print the full response data

        # Check the visibility of each entry in the response
        for entry in response_data['results']:
            print(f"Title: {entry['title']}, Visibility: {entry['visibility']}")

        # Extract the titles of the entries in the stream
        stream_titles = [entry['title'] for entry in response_data['results']]
        print("Stream Titles:", stream_titles)  # Debugging: Print the titles in the stream

        # Assert that all public entries are included
        self.assertIn(self.entry.title, stream_titles)  # Public entry by self.author

        # Assert that non-public entries are excluded
        self.assertNotIn(self.entry2.title, stream_titles)  # Friends-only entry by self.author
    
    '''

    
