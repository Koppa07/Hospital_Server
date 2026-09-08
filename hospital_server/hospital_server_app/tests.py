from rest_framework.test import APITestCase
from .models import User


class UserTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user", email="useremail@mail.ru", password="userpass"
        )
        self.client.force_authenticate(user=self.user)
        self.todo = Todo.objects.create(
            title="Test todo", description="Test description", owner=self.user
        )
        self.url = reverse("todo_details", kwargs={"pk": self.todo.pk})
