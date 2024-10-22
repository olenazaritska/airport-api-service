from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import AirplaneType, Airplane
from airport.serializers import AirplaneListSerializer, AirplaneDetailSerializer

AIRPLANE_LIST_URL = reverse("airport:airplane-list")
AIRPLANE_DETAIL_URL = reverse("airport:airplane-detail", kwargs={"pk": 1})


def sample_airplane_type(**params):
    defaults = {
        "name": "Sample_name",
    }
    defaults.update(params)
    return AirplaneType.objects.create(**defaults)


def sample_airplane(**params):
    defaults = {
        "name": "Sample_name",
        "rows": 40,
        "seats_in_row": 6,
        "airplane_type": sample_airplane_type(),
    }
    defaults.update(params)
    return Airplane.objects.create(**defaults)


class UnauthenticatedAirplaneAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(AIRPLANE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airplane_list(self):
        sample_airplane()
        response = self.client.get(AIRPLANE_LIST_URL)
        airplanes = Airplane.objects.all()
        serializer = AirplaneListSerializer(airplanes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airplane_retrieve(self):
        sample_airplane()
        response = self.client.get(AIRPLANE_DETAIL_URL)
        airplane = Airplane.objects.get(pk=1)
        serializer = AirplaneDetailSerializer(airplane)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airplane_create_forbidden(self):
        sample_airplane_type()
        data = {
            "name": "Sample_name",
            "rows": 40,
            "seats_in_row": 6,
            "airplane_type": 1,
        }
        response = self.client.post(
            AIRPLANE_LIST_URL,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airplane_create(self):
        sample_airplane_type()
        data = {
            "name": "Sample_name",
            "rows": 40,
            "seats_in_row": 6,
            "airplane_type": 1,
        }
        response = self.client.post(
            AIRPLANE_LIST_URL,
            data=data,
        )
        airplane = Airplane.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["name"], airplane.name)
        self.assertEqual(data["rows"], airplane.rows)
        self.assertEqual(data["seats_in_row"], airplane.seats_in_row)
        self.assertEqual(data["airplane_type"], airplane.airplane_type.id)

    def test_airplane_delete_not_allowed(self):
        sample_airplane()
        response = self.client.delete(AIRPLANE_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airplane_update_not_allowed(self):
        sample_airplane()
        data = {
            "name": "Sample_name",
            "rows": 50,
            "seats_in_row": 6,
            "airplane_type": 1
        }
        response = self.client.put(AIRPLANE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airplane_partial_update_not_allowed(self):
        sample_airplane()
        data = {"rows": 50}
        response = self.client.patch(AIRPLANE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
