from datetime import datetime, timezone, timedelta

from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import Airport, Route, AirplaneType, Airplane, Flight, Crew
from airport.serializers import FlightListSerializer, FlightDetailSerializer

FLIGHT_LIST_URL = reverse("airport:flight-list")
FLIGHT_DETAIL_URL = reverse("airport:flight-detail", kwargs={"pk": 1})


def get_flight_data():
    airport_source = Airport.objects.create(name="KRK", closest_big_city="Krakow")
    airport_destination = Airport.objects.create(name="PMI", closest_big_city="Palma")
    route = Route.objects.create(source=airport_source, destination=airport_destination, distance=1000)
    airplane_type = AirplaneType.objects.create(name="Boeing")
    airplane = Airplane.objects.create(
        name="BO1234",
        rows=40,
        seats_in_row=6,
        airplane_type=airplane_type,
    )
    data = {
        "route": route,
        "airplane": airplane,
        "departure_time": "2024-10-25T01:00:00Z",
        "arrival_time": "2024-10-25T02:00:00Z",
    }
    return data


def sample_flight(**params):
    if params:
        return Flight.objects.create(**params)
    data = get_flight_data()
    return Flight.objects.create(**data)


class UnauthenticatedFlightAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(FLIGHT_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_flight_list(self):
        sample_flight()
        response = self.client.get(FLIGHT_LIST_URL)

        flights = Flight.objects.all()
        serializer = FlightListSerializer(flights, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_flight_list_with_filters(self):
        sample_flight()
        airport_source = Airport.objects.get(name="PMI")
        airport_destination = Airport.objects.get(name="KRK")
        route = Route.objects.create(source=airport_source, destination=airport_destination, distance=1000)
        airplane = Airplane.objects.get(name="BO1234")
        data = {
            "route": route,
            "airplane": airplane,
            "departure_time": "2024-10-25T06:00:00.000Z",
            "arrival_time": "2024-10-25T07:00:00.000Z",
        }
        sample_flight(**data)

        response_source = self.client.get(
            FLIGHT_LIST_URL,
            {"source": str(airport_source.id)}
        )
        flights_source = Flight.objects.filter(route__source__id=airport_source.id)
        serializer_source = FlightListSerializer(flights_source, many=True)
        self.assertEqual(response_source.status_code, status.HTTP_200_OK)
        self.assertEqual(response_source.data["results"], serializer_source.data)

        response_destination = self.client.get(
            FLIGHT_LIST_URL,
            {"destination": str(airport_destination.id)}
        )
        flights_destination = Flight.objects.filter(route__destination__id=airport_destination.id)
        serializer_destination = FlightListSerializer(flights_destination, many=True)
        self.assertEqual(response_destination.status_code, status.HTTP_200_OK)
        self.assertEqual(response_destination.data["results"], serializer_destination.data)

        response_date = self.client.get(
            FLIGHT_LIST_URL,
            {"date": "2024-10-25"}
        )
        flights_date = Flight.objects.filter(departure_time__date="2024-10-25")
        serializer_date = FlightListSerializer(flights_date, many=True)
        self.assertEqual(response_date.status_code, status.HTTP_200_OK)
        self.assertEqual(response_date.data["results"], serializer_date.data)

    def test_flight_retrieve(self):
        sample_flight()
        response = self.client.get(FLIGHT_DETAIL_URL)

        flight = (
            Flight.objects
            .select_related("route", "airplane")
            .prefetch_related("crew")
            .annotate(
                tickets_available=(
                        F("airplane__rows") * F("airplane__seats_in_row")
                        - Count("tickets")
                )
            ).get(pk=1)
        )
        serializer = FlightDetailSerializer(flight)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_flight_create_forbidden(self):
        data = get_flight_data()
        data["route"] = data["route"].id
        data["airplane"] = data["airplane"].id

        response = self.client.post(FLIGHT_LIST_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminFlightAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_flight_create(self):
        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        data = get_flight_data()
        data["route"] = data["route"].id
        data["airplane"] = data["airplane"].id
        data["crew"] = [crew_member.id]

        response = self.client.post(FLIGHT_LIST_URL, data=data)

        flight = Flight.objects.get(pk=1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["route"], flight.route.id)
        self.assertEqual(data["airplane"], flight.airplane.id)

        departure_time = datetime.strptime(data["departure_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertEqual(departure_time, flight.departure_time)

        arrival_time = datetime.strptime(data["arrival_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertEqual(arrival_time, flight.arrival_time)

        self.assertEqual(data["crew"], [crew.id for crew in flight.crew.all()])

    def test_create_incorrent_departure_location_forbidden(self):
        flight_1 = sample_flight()

        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        data = {
            "route": flight_1.route.id,
            "airplane": flight_1.airplane.id,
            "departure_time": "2024-10-25T06:00:00Z",
            "arrival_time": "2024-10-25T07:00:00Z",
            "crew": crew_member.id
        }
        response = self.client.post(FLIGHT_LIST_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_arrival_time_before_departure_time_forbidden(self):
        data = get_flight_data()
        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        data["route"] = data["route"].id
        data["airplane"] = data["airplane"].id
        data["departure_time"] = data["arrival_time"]
        data["arrival_time"] = data["departure_time"]
        data["crew"] = [crew_member.id]

        response = self.client.post(FLIGHT_LIST_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_departure_before_previous_arrival_forbidden(self):
        flight_1 = sample_flight()
        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        route = Route.objects.create(
            source=flight_1.route.destination,
            destination=flight_1.route.source,
            distance=flight_1.route.distance
        )
        airplane = flight_1.airplane
        departure_time = flight_1.arrival_time - timedelta(hours=5)
        arrival_time = flight_1.arrival_time + timedelta(hours=5)
        flight_2_data = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "crew": [crew_member.id]
        }

        response = self.client.post(FLIGHT_LIST_URL, data=flight_2_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_before_airplane_rest_time_finished_forbidden(self):
        flight_1 = sample_flight()
        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        route = Route.objects.create(
            source=flight_1.route.destination,
            destination=flight_1.route.source,
            distance=flight_1.route.distance
        )
        airplane = flight_1.airplane
        departure_time = flight_1.arrival_time + timedelta(hours=1)
        arrival_time = flight_1.arrival_time + timedelta(hours=5)
        flight_2_data = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "crew": [crew_member.id]
        }

        response = self.client.post(FLIGHT_LIST_URL, data=flight_2_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_departure_time_exceeds_24_hours_after_previous_arrival_forbidden(self):
        flight_1 = sample_flight()
        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        route = Route.objects.create(
            source=flight_1.route.destination,
            destination=flight_1.route.source,
            distance=flight_1.route.distance
        )
        airplane = flight_1.airplane
        departure_time = flight_1.arrival_time + timedelta(hours=25)
        arrival_time = flight_1.arrival_time + timedelta(hours=30)
        flight_2_data = {
            "route": route.id,
            "airplane": airplane.id,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "crew": [crew_member.id]
        }

        response = self.client.post(FLIGHT_LIST_URL, data=flight_2_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flight_delete_not_allowed(self):
        sample_flight()
        response = self.client.delete(FLIGHT_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_flight_update_not_allowed(self):
        flight = sample_flight()

        crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        data = {
            "route": flight.route.id,
            "airplane": flight.airplane.id,
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time + timedelta(hours=1),
            "crew": [crew_member.id]
        }

        response = self.client.put(FLIGHT_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_flight_partial_update_not_allowed(self):
        flight = sample_flight()

        data = {
            "arrival_time": flight.arrival_time + timedelta(hours=1),
        }

        response = self.client.patch(FLIGHT_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
