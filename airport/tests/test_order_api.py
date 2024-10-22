from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from airport.models import Airport, Route, AirplaneType, Airplane, Flight, Order, Ticket
from airport.serializers import OrderListSerializer, OrderDetailSerializer

ORDER_LIST_URL = reverse("airport:order-list")
ORDER_DETAIL_URL = reverse("airport:order-detail", kwargs={"pk": 1})


def sample_flight(**params):
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
        "departure_time": timezone.now() + timedelta(days=1),
        "arrival_time": timezone.now() + timedelta(days=2),
    }
    if params:
        data.update(params)
    return Flight.objects.create(**data)


class UnauthenticatedOrderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ORDER_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_order_list(self):
        flight = sample_flight()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            flight=flight,
            order=order,
        )

        response = self.client.get(ORDER_LIST_URL)

        orders = Order.objects.all()
        serializer = OrderListSerializer(orders, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data["results"])

    def test_order_retrieve(self):
        flight = sample_flight()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            flight=flight,
            order=order,
        )

        response = self.client.get(ORDER_DETAIL_URL)
        serializer = OrderDetailSerializer(order)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_order_create(self):
        flight = sample_flight()
        ticket_1 = {
            "row": 1,
            "seat": 1,
            "flight": flight.pk,
        }
        ticket_2 = {
            "row": 1,
            "seat": 2,
            "flight": flight.pk,
        }
        data = {
            "tickets": [ticket_1, ticket_2],
        }
        response = self.client.post(ORDER_LIST_URL, data, format="json")

        order = Order.objects.get(pk=1)
        tickets = order.tickets.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ticket_1["row"], tickets[0].row)
        self.assertEqual(ticket_1["seat"], tickets[0].seat)
        self.assertEqual(ticket_1["flight"], tickets[0].flight.id)
        self.assertEqual(ticket_2["row"], tickets[1].row)
        self.assertEqual(ticket_2["seat"], tickets[1].seat)
        self.assertEqual(ticket_2["flight"], tickets[1].flight.id)

    def test_order_create_row_outside_given_range_forbidden(self):
        flight = sample_flight()
        ticket = {
            "row": 100,
            "seat": 1,
            "flight": flight.pk,
        }
        data = {
            "tickets": [ticket],
        }
        response = self.client.post(ORDER_LIST_URL, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_create_seat_outside_given_range_forbidden(self):
        flight = sample_flight()
        ticket = {
            "row": 1,
            "seat": 100,
            "flight": flight.pk,
        }
        data = {
            "tickets": [ticket],
        }
        response = self.client.post(ORDER_LIST_URL, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flight_row_seat_unique_constraint(self):
        flight = sample_flight()
        ticket_1 = {
            "row": 1,
            "seat": 1,
            "flight": flight.pk,
        }
        ticket_2 = {
            "row": 1,
            "seat": 1,
            "flight": flight.pk,
        }
        data = {
            "tickets": [ticket_1, ticket_2],
        }

        with self.assertRaises(ValidationError):
            self.client.post(ORDER_LIST_URL, data, format="json")

    def test_order_create_for_past_flights_forbidden(self):
        flight = sample_flight(departure_time=timezone.now() - timedelta(days=1))
        ticket = {
            "row": 1,
            "seat": 1,
            "flight": flight.pk,
        }
        data = {
            "tickets": [ticket],
        }
        response = self.client.post(ORDER_LIST_URL, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_delete_not_allowed(self):
        flight = sample_flight()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            flight=flight,
            order=order,
        )

        response = self.client.delete(ORDER_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_order_update_not_allowed(self):
        flight = sample_flight()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            flight=flight,
            order=order,
        )
        data = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 2,
                    "flight": 1
                }
            ]
        }

        response = self.client.put(ORDER_DETAIL_URL, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_order_partial_update_not_allowed(self):
        flight = sample_flight()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            flight=flight,
            order=order,
        )
        data = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 2,
                    "flight": 1
                }
            ]
        }

        response = self.client.patch(ORDER_DETAIL_URL, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
