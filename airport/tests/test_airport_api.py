from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import Airport
from airport.serializers import AirportSerializer

AIRPORT_LIST_URL = reverse("airport:airport-list")
AIRPORT_DETAIL_URL = reverse("airport:airport-detail", kwargs={"pk": 1})


def sample_airport(**params):
    defaults = {
        "name": "Sample_name",
        "closest_big_city": "Sample_city"
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


class UnauthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(AIRPORT_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airport_list(self):
        sample_airport()
        response = self.client.get(AIRPORT_LIST_URL)
        airports = Airport.objects.all()
        serializer = AirportSerializer(airports, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airport_retrieve(self):
        sample_airport()
        response = self.client.get(AIRPORT_DETAIL_URL)
        airport = Airport.objects.get(pk=1)
        serializer = AirportSerializer(airport)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_airport_create_forbidden(self):
        response = self.client.post(
            AIRPORT_LIST_URL,
            {"name": "Sample_name",
             "closest_big_city": "Sample_city"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_airport_create(self):
        data = {"name": "Sample_name", "closest_big_city": "Sample_city"}
        response = self.client.post(
            AIRPORT_LIST_URL,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        airport = Airport.objects.get(pk=1)
        self.assertEqual(airport.name, data["name"])
        self.assertEqual(airport.closest_big_city, data["closest_big_city"])

    def test_airport_delete_not_allowed(self):
        sample_airport()
        response = self.client.delete(AIRPORT_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airport_update_not_allowed(self):
        sample_airport()
        data = {"name": "Sample_name_new", "closest_big_city": "Sample_city_new"}
        response = self.client.put(AIRPORT_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_airport_partial_update_not_allowed(self):
        sample_airport()
        data = {"name": "Sample_name_new"}
        response = self.client.patch(AIRPORT_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
