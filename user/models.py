from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.username} ({self.first_name} {self.last_name})"
