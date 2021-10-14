from django.test import Client, TestCase 


class CoreURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()
    
    def test_pages(self):
        """Cтраница 404 отдает кастомный шаблон."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')
