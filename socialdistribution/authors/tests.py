from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from authors.models import Author, FollowRequest, FollowRequestStatus
from entries.models import Entry, Visibility


class AuthorProfileViewTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="janedoe",
            password="testpass123",
            display_name="Jane Doe",
            github="https://github.com/janedoe",
            profile_image="https://example.com/avatar.png",
        )
        self.public_entry = Entry.objects.create(
            title="Public Post",
            description="Visible to everyone",
            content="Public content",
            author=self.author,
            visibility=Visibility.PUBLIC,
        )
        self.private_entry = Entry.objects.create(
            title="Friends Post",
            description="For friends only",
            content="Private content",
            author=self.author,
            visibility=Visibility.FRIENDS,
        )

    def test_profile_page_renders_public_information(self):
        url = reverse("authors:profile_detail", args=[self.author.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authors/profile_detail.html")
        self.assertContains(response, self.author.display_name)
        self.assertContains(response, self.public_entry.title)
        self.assertNotContains(response, self.private_entry.title)

    def test_get_absolute_url_points_to_profile(self):
        self.assertEqual(
            self.author.get_absolute_url(),
            reverse("authors:profile_detail", args=[self.author.id]),
        )

class AuthorAPITests(TestCase):
    '''
    All tests for the author APIs
    '''
    def setUp(self):
        self.client = APIClient()
        self.user1 = Author.objects.create_user(
            username='john',
            password='pass123',
            display_name='John Doe',
            github='https://github.com/john',
            is_approved=True
        )
        self.user2 = Author.objects.create_user(
            username='jane',
            password='passwd1234',
            display_name='Jane Smith',
            github='https://github.com/jane',
            is_approved=True
        )
    def test_get_author_profile(self):
        """
        Test: As an author, I want a public page with my profile information
        API: GET /api/authors/{AUTHOR_ID}/
        """
        # Make request
        response = self.client.get(f'/api/authors/{self.user1.id}/')
        
        # Assert status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Assert response structure
        self.assertEqual(response.data['type'], 'author')
        self.assertEqual(response.data['displayName'], 'John Doe')
        self.assertEqual(response.data['github'], 'https://github.com/john')
        self.assertIn('id', response.data)
        self.assertIn('host', response.data)

    def test_get_all_profiles(self):
        """
        Test: Getting all profiles from the node
        API: GET /api/authors/
        """
        # Make request
        response = self.client.get(f'/api/authors/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
        # Check pagination structure
        self.assertIn('results', response.data)
               
        # Should have 2 authors
        authors_list = response.data['results']
        self.assertEqual(len(authors_list), 2)
        
        # Check that all authors have required fields
        for author in authors_list:
            self.assertEqual(author['type'], 'author')
            self.assertIn('id', author)
            self.assertIn('displayName', author)
            self.assertIn('host', author)
            self.assertIn('github', author)
            self.assertIn('profileImage', author)
        
        # Check that both users display names exist in the results
        display_names = [a['displayName'] for a in authors_list]
        self.assertIn('John Doe', display_names) 
        self.assertIn('Jane Smith', display_names)





class FollowRequestViewTests(TestCase):
    def setUp(self):
        self.follower = Author.objects.create_user(
            username="alice",
            password="password123",
            display_name="Alice",
            is_approved=True,
        )
        self.followee = Author.objects.create_user(
            username="bob",
            password="password123",
            display_name="Bob",
            is_approved=True,
        )

    def test_send_follow_request_creates_pending_request(self):
        self.client.force_login(self.follower)
        url = reverse("authors:send_follow_request", args=[self.followee.id])

        response = self.client.post(url)

        self.assertRedirects(response, self.followee.get_absolute_url())
        follow_request = FollowRequest.objects.get(follower=self.follower, followee=self.followee)
        self.assertEqual(follow_request.status, FollowRequestStatus.PENDING)

    def test_followee_can_approve_request(self):
        follow_request = FollowRequest.objects.create(
            follower=self.follower,
            followee=self.followee,
            status=FollowRequestStatus.PENDING,
        )
        self.client.force_login(self.followee)
        url = reverse("authors:approve_follow_request", args=[follow_request.id])

        response = self.client.post(url)

        self.assertRedirects(response, reverse("authors:follow_requests"))
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, FollowRequestStatus.APPROVED)

    def test_followee_can_deny_request(self):
        follow_request = FollowRequest.objects.create(
            follower=self.follower,
            followee=self.followee,
            status=FollowRequestStatus.PENDING,
        )
        self.client.force_login(self.followee)
        url = reverse("authors:deny_follow_request", args=[follow_request.id])

        response = self.client.post(url)

        self.assertRedirects(response, reverse("authors:follow_requests"))
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.status, FollowRequestStatus.REJECTED)

    def test_follower_can_unfollow_after_approval(self):
        FollowRequest.objects.create(
            follower=self.follower,
            followee=self.followee,
            status=FollowRequestStatus.APPROVED,
        )
        self.client.force_login(self.follower)
        url = reverse("authors:unfollow_author", args=[self.followee.id])

        response = self.client.post(url)

        self.assertRedirects(response, self.followee.get_absolute_url())
        self.assertFalse(
            FollowRequest.objects.filter(follower=self.follower, followee=self.followee).exists()
        )

class ProfileEditTests(TestCase):
    def setUp(self):
        """
        Set up test data for the profile edit functionality.
        """
        self.author = Author.objects.create_user(
            username="janedoe",
            password="testpass123",
            display_name="Jane Doe",
            github="https://github.com/janedoe",
            profile_image="https://example.com/avatar.png",
        )
        self.other_author = Author.objects.create_user(
            username="johnsmith",
            password="testpass123",
            display_name="John Smith",
            github="https://github.com/johnsmith",
            profile_image="https://example.com/avatar2.png",
        )
        self.client.force_login(self.author)  # Log in as the author

    def test_author_can_edit_profile(self):
        """
        Test that an author can edit their profile.
        """
        edit_url = reverse("authors:profile_edit", kwargs={"author_id": self.author.id})
        new_data = {
            "display_name": "Updated Jane Doe",
            "github": "https://github.com/updatedjanedoe",
            "profile_image": "https://example.com/updated_avatar.png",
        }

        # Send a POST request to update the profile
        response = self.client.post(edit_url, new_data)

        # Assert the response redirects to the stream page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("stream"))

        # Refresh the author object from the database
        self.author.refresh_from_db()

        # Assert the author's profile was updated
        self.assertEqual(self.author.display_name, new_data["display_name"])
        self.assertEqual(self.author.github, new_data["github"])
        self.assertEqual(self.author.profile_image, new_data["profile_image"])

    def test_author_cannot_edit_another_authors_profile(self):
        """
        Test that an author cannot edit another author's profile.
        """
        edit_url = reverse("authors:profile_edit", kwargs={"author_id": self.other_author.id})
        new_data = {
            "display_name": "Malicious Update",
            "github": "https://github.com/malicious",
            "profile_image": "https://example.com/malicious_avatar.png",
        }

        # Send a POST request to update another author's profile
        response = self.client.post(edit_url, new_data)

        # Assert the response redirects to the stream page with an error
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("stream"))

        # Refresh the other author object from the database
        self.other_author.refresh_from_db()

        # Assert the other author's profile was not updated
        self.assertNotEqual(self.other_author.display_name, new_data["display_name"])
        self.assertNotEqual(self.other_author.github, new_data["github"])
        self.assertNotEqual(self.other_author.profile_image, new_data["profile_image"])