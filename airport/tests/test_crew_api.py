from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import Crew
from airport.serializers import CrewListSerializer, CrewSerializer

CREW_LIST_URL = reverse("airport:crew-list")
CREW_DETAIL_URL = reverse("airport:crew-detail", kwargs={"pk": 1})


def sample_crew_member(**params):
    defaults = {
        "first_name": "John",
        "last_name": "Doe"
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)


class UnauthenticatedCrewAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(CREW_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_crew_list(self):
        sample_crew_member()
        response = self.client.get(CREW_LIST_URL)
        crew = Crew.objects.all()
        serializer = CrewListSerializer(crew, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_crew_detail(self):
        member = sample_crew_member()
        response = self.client.get(CREW_DETAIL_URL)
        serializer = CrewSerializer(member)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_crew_create_forbidden(self):
        response = self.client.post(
            CREW_LIST_URL,
            {"first_name": "Test_name", "last_name": "Test_surname"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminCrewAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_crew_create(self):
        data = {"first_name": "Test_name", "last_name": "Test_surname"}
        response = self.client.post(
            CREW_LIST_URL,
            data=data
        )
        member = Crew.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["first_name"], member.first_name)
        self.assertEqual(data["last_name"], member.last_name)

    def test_crew_update(self):
        sample_crew_member()
        data = {"first_name": "Test_name", "last_name": "Test_surname"}
        response = self.client.put(
            CREW_DETAIL_URL,
            data=data
        )
        member = Crew.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["first_name"], member.first_name)
        self.assertEqual(data["last_name"], member.last_name)

    def test_crew_partial_update(self):
        sample_crew_member()
        data = {"first_name": "Test_name"}
        response = self.client.patch(
            CREW_DETAIL_URL,
            data=data
        )
        member = Crew.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["first_name"], member.first_name)

    def test_crew_delete(self):
        sample_crew_member()
        response = self.client.delete(CREW_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
