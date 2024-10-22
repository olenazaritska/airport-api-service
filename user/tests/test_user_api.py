from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.serializers import UserSerializer

USER_CREATE_URL = reverse("user:create")
USER_MANAGE_URL = reverse("user:manage")


class UnauthenticatedUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_user(self):
        data = {
            "email": "test@test.com",
            "password": "test123"
        }
        response = self.client.post(USER_CREATE_URL, data)

        user = get_user_model().objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["email"], user.email)
        self.assertTrue(user.check_password(data["password"]))

    def test_user_manage_auth_required(self):
        response = self.client.get(USER_MANAGE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_user_retrieve(self):
        response = self.client.get(USER_MANAGE_URL)
        serializer = UserSerializer(instance=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_user_update(self):
        data = {
            "email": "test_new@test.com",
            "password": "password987"
        }
        response = self.client.put(USER_MANAGE_URL, data)

        user = get_user_model().objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.email, data["email"])
        self.assertTrue(user.check_password(data["password"]))

    def test_user_partial_update(self):
        data = {
            "email": "test_new@test.com",
        }
        response = self.client.patch(USER_MANAGE_URL, data)

        user = get_user_model().objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.email, data["email"])

    def test_user_delete_forbidden(self):
        response = self.client.delete(USER_MANAGE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
