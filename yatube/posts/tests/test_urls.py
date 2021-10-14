from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user1 = User.objects.get(username='TestUser')
        self.user2 = User.objects.create_user(username='HasNoName')
        self.authorized_client1 = Client()
        self.authorized_client2 = Client()
        self.authorized_client1.force_login(self.user1)
        self.authorized_client2.force_login(self.user2)
        cache.clear()

    def test_pages_for_each_user(self):
        """Страницы доступны любому пользователю."""
        urls = [
            '/',
            f'/group/{PostsURLTests.group.slug}/',
            f'/profile/{PostsURLTests.user.username}/',
            f'/posts/{PostsURLTests.post.id}/',
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_for_authorized_user(self):
        """Страницы доступны авторизированному пользователю."""
        response = self.authorized_client1.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_edit_post_for_author(self):
        """Страница по адресу /posts/<post_id>/edit/
        доступна для автора поста.
        """
        response = self.authorized_client1.get(
            f'/posts/{PostsURLTests.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """Запрос к несуществующей странице"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_page_edit_post_for_not_author(self):
        """Страница по адресу /posts/<post_id>/edit/ перенаправит не
        автора поста на страницу /posts/<post_id>/.
        """
        response = self.authorized_client2.get(
            f'/posts/{PostsURLTests.post.id}/edit/'
        )
        self.assertRedirects(
            response, f'/posts/{PostsURLTests.post.id}/'
        )

    def test_page_edit_post_for_not_author(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/')
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostsURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostsURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{PostsURLTests.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostsURLTests.post.id}/edit/': 'posts/create_post.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client1.get(adress)
                self.assertTemplateUsed(response, template)
