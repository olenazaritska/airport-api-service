from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from airport.models import Airport, Route, Crew, AirplaneType, Airplane, Flight, Ticket, Order


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("source", "destination", "distance")

    def validate(self, data):
        Route.validate_route(data["source"], data["destination"], ValidationError)
        return data


class RouteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "full_route", "distance")


class RouteDetailSerializer(RouteSerializer):
    source = AirportSerializer(read_only=True)
    destination = AirportSerializer(read_only=True)


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name")


class CrewListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "full_name")


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ("id", "name", "rows", "seats_in_row", "airplane_type")


class AirplaneListSerializer(serializers.ModelSerializer):
    airplane_type = serializers.SlugRelatedField(read_only=True, slug_field="name")

    class Meta:
        model = Airplane
        fields = ("id", "name", "capacity", "airplane_type")


class AirplaneDetailSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(read_only=True, slug_field="name")


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "departure_time", "arrival_time", "crew")

    def validate(self, data):
        airplane = data.get("airplane")
        route = data.get("route")
        departure_time = data.get("departure_time")
        arrival_time = data.get("arrival_time")

        previous_flight = (
            Flight.objects
            .filter(airplane=airplane)
            .order_by('-arrival_time')
            .first()
        )
        previous_arrival_time = None

        if previous_flight:
            previous_arrival_time = previous_flight.arrival_time

            available_routes = Route.objects.filter(source=previous_flight.route.destination)
            available_route_list = None
            if available_routes:
                available_route_list = ", ".join([route.full_route for route in available_routes])

            Flight.validate_flight_departure_location(
                route.source,
                previous_flight.route.destination,
                available_route_list,
                ValidationError
            )

        Flight.validate_flight_time(
            departure_time,
            arrival_time,
            previous_arrival_time,
            ValidationError
        )

        return data


class FlightListSerializer(FlightSerializer):
    route = serializers.SlugRelatedField(read_only=True, slug_field="full_route")
    airplane = serializers.SlugRelatedField(read_only=True, slug_field="name")
    departure_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    arrival_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    crew = serializers.SlugRelatedField(many=True, read_only=True, slug_field="full_name")


class TicketSeatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class FlightDetailSerializer(serializers.ModelSerializer):
    full_route = serializers.CharField(source="route.full_route", read_only=True)
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)
    airplane_capacity = serializers.IntegerField(source="airplane.capacity", read_only=True)
    departure_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    arrival_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    tickets_available = serializers.IntegerField(read_only=True)
    taken_places = TicketSeatsSerializer(
        source="tickets", many=True, read_only=True
    )
    crew = serializers.SlugRelatedField(many=True, read_only=True, slug_field="full_name")

    class Meta:
        model = Flight
        fields = (
            "id",
            "full_route",
            "departure_time",
            "arrival_time",
            "airplane_name",
            "airplane_capacity",
            "tickets_available",
            "taken_places",
            "crew",
        )


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight")

    def validate(self, attrs):
        data = super().validate(attrs=attrs)
        Ticket.validate_ticket_row_seat(
            attrs["row"],
            attrs["seat"],
            attrs["flight"].airplane,
            ValidationError
        )
        return data


class TicketDetailSerializer(TicketSerializer):
    flight = FlightListSerializer(read_only=True)


class TicketListSerializer(serializers.ModelSerializer):
    route = serializers.CharField(source="flight.route.full_route", read_only=True)
    departure_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="flight.departure_time", read_only=True)
    arrival_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", source="flight.arrival_time", read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "route", "departure_time", "arrival_time")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def validate(self, attrs):
        data = super().validate(attrs=attrs)
        created_at = self.instance.created_at if self.instance else timezone.now()

        for ticket in data["tickets"]:
            Ticket.validate_ticket_flight(
                created_at,
                ticket["flight"].departure_time,
                ValidationError
            )
        return data

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    tickets = TicketListSerializer(many=True, read_only=True)


class OrderDetailSerializer(OrderSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    tickets = TicketDetailSerializer(many=True, read_only=True)
