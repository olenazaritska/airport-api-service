from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import AirplaneType
from airport.serializers import AirplaneTypeSerializer

AIRPLANE_TYPE_LIST_URL = reverse("airport:airplanetype-list")
AIRPLANE_TYPE_DETAIL_URL = reverse("airport:airplanetype-detail", kwargs={"pk": 1})


def sample_airplane_type(**params):
    defaults = {
        "name": "Sample_name",
    }
    defaults.update(params)
    return AirplaneType.objects.create(**defaults)


class UnauthenticatedAirplaneTypeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(AIRPLANE_TYPE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneTypeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airplane_type_list(self):
        sample_airplane_type()
        response = self.client.get(AIRPLANE_TYPE_LIST_URL)
        airplane_types = AirplaneType.objects.all()
        serializer = AirplaneTypeSerializer(airplane_types, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airplane_type_retrieve(self):
        sample_airplane_type()
        response = self.client.get(AIRPLANE_TYPE_DETAIL_URL)
        airplane_type = AirplaneType.objects.get(pk=1)
        serializer = AirplaneTypeSerializer(airplane_type)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airplane_type_create_forbidden(self):
        response = self.client.post(
            AIRPLANE_TYPE_LIST_URL,
            data={"name": "Sample_name"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneTypeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airplane_type_create(self):
        data = {"name": "Sample_name"}
        response = self.client.post(
            AIRPLANE_TYPE_LIST_URL,
            data=data
        )
        airplane_type = AirplaneType.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(airplane_type.name, data["name"])

    def test_airplane_type_delete_not_allowed(self):
        sample_airplane_type()
        response = self.client.delete(AIRPLANE_TYPE_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airplane_type_update_not_allowed(self):
        sample_airplane_type()
        data = {"name": "Sample_name_new"}
        response = self.client.put(AIRPLANE_TYPE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airplane_type_partial_update_not_allowed(self):
        sample_airplane_type()
        data = {"name": "Sample_name_new"}
        response = self.client.patch(AIRPLANE_TYPE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
