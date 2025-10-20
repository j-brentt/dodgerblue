from django.test import TestCase
from django.urls import reverse

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
