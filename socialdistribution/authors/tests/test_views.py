from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from authors.models import Author  
from entries.models import Entry, Visibility 
import uuid


class AuthorAndEntryURLTests(APITestCase):
    def setUp(self):
        """
        Set up test data for authors and entries.
        """
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
        self.entry = Entry.objects.create(
            id=uuid.uuid4(),
            title="Test Entry",
            description="This is a brief description of the entry.",
            content="This is a test entry.",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )

    def test_author_url_consistency(self):
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

    def test_entry_url_consistency(self):
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

    def test_author_list(self):
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
    
    def test_author_detail(self):
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

    def test_author_profile_page(self):
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