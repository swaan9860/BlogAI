from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Post, Category

class PostTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Test', slug='test')

    def test_post_creation(self):
        post = Post.objects.create(
            title='Test Post',
            content='Content',
            author=self.user,
            category=self.category,
            slug='test-post'
        )
        self.assertEqual(post.title, 'Test Post')
        self.assertEqual(post.author.username, 'testuser')