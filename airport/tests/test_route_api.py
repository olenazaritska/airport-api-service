from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import Airport, Route
from airport.serializers import RouteListSerializer, RouteDetailSerializer

ROUTE_LIST_URL = reverse("airport:route-list")
ROUTE_DETAIL_URL = reverse("airport:route-detail", kwargs={"pk": 1})


def sample_airport(**params):
    defaults = {
        "name": "Sample_name",
        "closest_big_city": "Sample_city"
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_route(**params):
    if params:
        return Route.objects.create(**params)
    defaults = {
        "source": sample_airport(),
        "destination": sample_airport(name="Sample_name_1", closest_big_city="Sample_city_1"),
        "distance": 1000,
    }
    return Route.objects.create(**defaults)


class UnauthenticatedRouteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ROUTE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_route_list(self):
        sample_route()
        response = self.client.get(ROUTE_LIST_URL)
        routes = Route.objects.all()
        serializer = RouteListSerializer(routes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_route_retrieve(self):
        route = sample_route()
        response = self.client.get(ROUTE_DETAIL_URL)
        serializer = RouteDetailSerializer(route)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_route_list_with_filters(self):
        sample_route()

        source = sample_airport(name="Sample_name_2", closest_big_city="Sample_city_2")
        destination = sample_airport(name="Sample_name_3", closest_big_city="Sample_city_3")
        sample_route(source=source, destination=destination, distance=1000)

        response = self.client.get(
            ROUTE_LIST_URL,
            {"source": str(source.id), "destination": str(destination.id)}
        )
        routes = Route.objects.filter(source__id=source.id, destination__id=destination.id)
        serializer = RouteListSerializer(routes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_route_create_forbidden(self):
        source = sample_airport()
        destination = sample_airport(name="Sample_name_1", closest_big_city="Sample_city_1")

        response = self.client.post(
            ROUTE_LIST_URL,
            {"source": source.id, "destination": destination.id, "distance": 1000}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminRouteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_route_create(self):
        source = sample_airport()
        destination = sample_airport(name="Sample_name_1", closest_big_city="Sample_city_1")

        data = {"source": source.id, "destination": destination.id, "distance": 1000}

        response = self.client.post(
            ROUTE_LIST_URL,
            data=data
        )

        route = Route.objects.get(pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["source"], route.source.id)
        self.assertEqual(data["destination"], route.destination.id)
        self.assertEqual(data["distance"], route.distance)

    def test_create_route_with_different_source_and_destination(self):
        airport = sample_airport()

        response = self.client.post(
            ROUTE_LIST_URL,
            {"source": airport.id, "destination": airport.id, "distance": 1000}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_route_delete_not_allowed(self):
        sample_route()
        response = self.client.delete(ROUTE_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_route_update_not_allowed(self):
        sample_route()

        source = sample_airport(name="Sample_name_2", closest_big_city="Sample_city_2")
        destination = sample_airport(name="Sample_name_3", closest_big_city="Sample_city_3")
        data = {
            "source": source.id,
            "destination": destination.id,
            "distance": 1500,
        }
        response = self.client.put(ROUTE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_route_partial_update_not_allowed(self):
        sample_route()

        source = sample_airport(name="Sample_name_2", closest_big_city="Sample_city_2")
        data = {
            "source": source.id,
        }
        response = self.client.patch(ROUTE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
