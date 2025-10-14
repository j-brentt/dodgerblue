from django.test import TestCase
from django.urls import reverse

from authors.models import Author
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