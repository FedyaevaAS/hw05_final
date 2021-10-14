import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Comment, Post

TEMP_POSTS_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_POSTS_ROOT)
class PostsCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.user,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_POSTS_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.get(username='TestUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """При отправке валидной формы со страницы создания поста
        создаётся новая запись в базе данных.
        """
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                author=PostsCreateFormTests.user,
                image=f'posts/{uploaded.name}',
                group=None
            ).exists()
        )

    def test_edit_post(self):
        """При отправке валидной формы со страницы редактирования поста
        происходит изменение поста с post_id в базе данных.
        """
        post = Post.objects.all().first()
        form_data = {
            'text': 'Тестовый текст изменен',
        }
        self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
            instance=post
        )
        self.assertEqual(Post.objects.all().first().text, form_data['text'])

    def test_send_comment(self):
        """Комментировать посты может только авторизованный пользователь.
        После успешной отправки комментарий появляется на странице поста.
        """
        comments_count = Comment.objects.count()
        form_data1 = {
            'text': 'Тестовый комментарий1',
        }
        form_data2 = {
            'text': 'Тестовый комментарий2',
        }
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            ),
            data=form_data1,
            follow=True
        )
        self.client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            ),
            data=form_data2,
            follow=True
        )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            )
        )
        self.assertEqual(
            form_data1['text'],
            response.context['comments'][0].text
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
