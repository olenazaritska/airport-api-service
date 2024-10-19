from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models

from airport_api_service import settings


class Airport(models.Model):
    name = models.CharField(max_length=255, unique=True)
    closest_big_city = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="source_routes")
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="destination_routes")
    distance = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "destination"], name="unique_route")
        ]

    @property
    def full_route(self):
        return f"{self.source.name} - {self.destination.name}"

    @staticmethod
    def validate_route(source, destination, error_to_raise):
        if source == destination:
            raise error_to_raise("Source and destination airports must be different.")

    def clean(self):
        Route.validate_route(self.source, self.destination, ValidationError)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_route


class Crew(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class AirplaneType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(
        AirplaneType,
        on_delete=models.CASCADE,
        related_name="airplanes"
    )

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Flight(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="flights")
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE, related_name="flights")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, related_name="flights")

    class Meta:
        ordering = ["departure_time", "arrival_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["airplane", "departure_time"],
                name="unique_flight"
            )
        ]

    @staticmethod
    def validate_flight_time(
            departure_time,
            arrival_time,
            previous_arrival_time,
            error_to_raise
    ):
        if departure_time >= arrival_time:
            raise error_to_raise("Departure time must be earlier than arrival time.")

        if previous_arrival_time:
            if departure_time < previous_arrival_time:
                next_possible_departure = previous_arrival_time + timedelta(hours=3)
                raise error_to_raise(
                    f"Cannot schedule this flight before the previous flight arrives. "
                    f"The airplane's last scheduled flight arrives at {previous_arrival_time}. "
                    f"The next possible departure time is {next_possible_departure}."
                )
            if departure_time < previous_arrival_time + timedelta(hours=3):
                next_possible_departure = previous_arrival_time + timedelta(hours=3)
                raise error_to_raise(
                    f"The airplane needs a 3-hour rest after its previous flight. "
                    f"The previous flight arrived at {previous_arrival_time}. "
                    f"The next available departure time is {next_possible_departure}."
                )

            time_difference = departure_time - previous_arrival_time
            if time_difference > timedelta(hours=24):
                raise error_to_raise(
                    f"The time difference between consecutive flights shouldn't exceed 24 hours. "
                    f"Previous flight arrived at {previous_arrival_time}, "
                    f"and this flight is scheduled to depart at {departure_time}."
                )

    @staticmethod
    def validate_flight_departure_location(
            source,
            previous_destination,
            available_route_list,
            error_to_raise
    ):
        if source != previous_destination:
            if available_route_list:
                raise error_to_raise(
                    "Departure location should match the arrival location of the previous flight. "
                    f"Available routes with the correct departure location: {available_route_list}."
                )
            else:
                raise error_to_raise(
                    "Departure location should match the arrival location of the previous flight. "
                    "There are no routes with the correct departure location. "
                    "You need to create a route first, then schedule the flight."
                )

    def clean(self):
        super().clean()

        previous_flight = (
            Flight.objects
            .filter(airplane=self.airplane)
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
                self.route.source,
                previous_flight.route.destination,
                available_route_list,
                ValidationError
            )

        Flight.validate_flight_time(
            self.departure_time,
            self.arrival_time,
            previous_arrival_time,
            ValidationError
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.route.full_route} "
            f"({self.departure_time.strftime("%Y-%m-%d %H:%M:%S")} - "
            f"{self.arrival_time.strftime("%Y-%m-%d %H:%M:%S")})"
        )


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.created_at.strftime("%Y-%m-%d %H:%M:%S"))


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["flight", "row", "seat"], name="unique_ticket")
        ]
        ordering = ["row", "seat"]

    @staticmethod
    def validate_ticket_row_seat(row, seat, airplane, error_to_raise):
        for ticket_attr_value, ticket_attr_name, airplane_attr_name in [
            (row, "row", "rows"),
            (seat, "seat", "seats_in_row"),
        ]:
            count_attrs = getattr(airplane, airplane_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                                          f"number must be in available range: "
                                          f"(1, {airplane_attr_name}): "
                                          f"(1, {count_attrs})"
                    }
                )

    @staticmethod
    def validate_ticket_flight(
            order_created_at,
            flight_departure_time,
            error_to_raise
    ):
        if order_created_at > flight_departure_time:
            raise error_to_raise(
                {"order": "Booking for past flights is not available. "
                          f"Order created at {order_created_at} "
                          f"but the flight departs at {flight_departure_time}."}
            )

    def clean(self):
        Ticket.validate_ticket_row_seat(
            self.row,
            self.seat,
            self.flight.airplane,
            ValidationError,
        )

        Ticket.validate_ticket_flight(
            self.order.created_at,
            self.flight.departure_time,
            ValidationError
        )

    def save(
            self,
            *args,
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None,
    ):
        self.full_clean()
        return super().save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return (
            f"{str(self.flight)} (row: {self.row}, seat: {self.seat})"
        )
