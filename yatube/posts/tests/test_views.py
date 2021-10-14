from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from yatube.settings import posts_per_page

from ..models import Group, Post

User = get_user_model()


class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='TestUser')
        cls.group1 = Group.objects.create(
            title='Тестовая группа1',
            slug='test-slug1',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание',
        )
        for i in range(2, 15):
            cls.post = Post.objects.create(
                text='Тестовая запись',
                author=cls.user,
                group=cls.group1,
                id=i,
            )
        cls.post = Post.objects.create(
            text='Пост с группой2',
            author=cls.user,
            group=cls.group2,
            image=cls.uploaded,
            id=1,
        )

    def setUp(self):
        self.user1 = User.objects.get(username='TestUser')
        self.user2 = User.objects.create_user(username='HasNoName')
        self.authorized_client1 = Client()
        self.authorized_client2 = Client()
        self.authorized_client1.force_login(self.user1)
        self.authorized_client2.force_login(self.user2)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewTests.group1.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': 1}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': 1}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client1.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно posts_per_page."""
        test_pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewTests.group1.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': PostsViewTests.user.username}
            )
        ]
        for page in test_pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    posts_per_page
                )

    def test_index_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client1.get(reverse('posts:index'))
        self.assertEqual(
            response.context['page_obj'][:posts_per_page],
            list(Post.objects.all()[:posts_per_page])
        )

    def test_group_list_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client1.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewTests.group1.slug}
            )
        )
        self.assertEqual(
            response.context['page_obj'][:posts_per_page],
            list(
                Post.objects.filter(
                    group=PostsViewTests.group1
                )[:posts_per_page]
            )
        )

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client1.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(
            response.context['page_obj'][:posts_per_page],
            list(
                Post.objects.filter(
                    author=PostsViewTests.user
                )[:posts_per_page]
            )
        )

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client1.get(
            reverse('posts:post_detail', kwargs={'post_id': 1})
        )
        self.assertEqual(
            response.context['post'],
            Post.objects.get(id=1)
        )

    def test_create_correct_context(self):
        """Шаблоны post_create, post_edit
        сформированы с правильным контекстом.
        """
        template_form_fields = {
            reverse('posts:post_create'): ['text', forms.fields.CharField],
            reverse(
                'posts:post_edit',
                kwargs={'post_id': 1}
            ): ['group', forms.fields.ChoiceField],
        }
        for template, value_expected in template_form_fields.items():
            with self.subTest(template=template):
                response = self.authorized_client1.get(template)
                form_field = response.context.get('form').fields.get(
                    value_expected[0]
                )
                self.assertIsInstance(form_field, value_expected[1])

    def test_new_post_with_group(self):
        """Пост с group2 появляется на главной странице сайта,
        на странице выбранной группы, в профайле пользователя и
        не попал в группу, для которой не был предназначен.
        """
        post_with_group2 = Post.objects.get(group=PostsViewTests.group2)
        templates = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewTests.group2.slug}
            ),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for template in templates:
            with self.subTest(template=template):
                response = self.authorized_client1.get(template)
                self.assertIn(
                    post_with_group2,
                    list(response.context['page_obj'])
                )
        response = self.authorized_client1.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewTests.group1.slug}
            )
        )
        self.assertNotIn(post_with_group2, list(response.context['page_obj']))

    def test_add_image(self):
        """При выводе поста с картинкой изображение
        передаётся в словаре context.
        """
        contexts_pages = {
            'page_obj': [
                reverse('posts:index'),
                reverse(
                    'posts:group_list',
                    kwargs={'slug': PostsViewTests.group2.slug}
                ),
                reverse(
                    'posts:profile',
                    kwargs={'username': self.user.username}
                )
            ],
            'post': reverse('posts:post_detail', kwargs={'post_id': 1})
        }
        for context, pages in contexts_pages.items():
            with self.subTest(context=context):
                if type(pages) is list:
                    for page in pages:
                        with self.subTest(page=page):
                            response = self.client.get(page)
                            objects = response.context[context]
                            images = list(map(lambda x: x.image, objects))
                            self.assertIn(Post.objects.get(id=1).image, images)
                else:
                    response = self.client.get(pages)
                    object = response.context[context]
                    post_image = object.image
                    self.assertEqual(post_image, Post.objects.get(id=1).image)

    def test_cache(self):
        """Проверка работы кеша."""
        form_data = {
            'text': 'Тестовый текст'
        }
        response1 = self.client.get(reverse('posts:index'))
        self.authorized_client1.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        response2 = self.client.get(reverse('posts:index'))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.client.get('posts:index')
        self.assertNotEqual(response1.content, response3.content)

    def test_follow_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок.
        """
        author = self.user
        self.authorized_client2.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': author.username}
            )
        )
        self.assertIn(
            author.id,
            self.user2.follower.values_list('author', flat=True)
        )
        self.authorized_client2.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': author.username}
            )
        )
        self.assertNotIn(
            author.id,
            self.user2.follower.values_list('author', flat=True)
        )

    def test_new_post_follow(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        response1 = self.authorized_client2.get(
            reverse('posts:follow_index')
        )
        self.assertNotContains(response1, self.post)
        self.authorized_client2.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}
            )
        )
        response2 = self.authorized_client2.get(
            reverse('posts:follow_index')
        )
        self.assertContains(response2, self.post)
