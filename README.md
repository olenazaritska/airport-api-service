# Airport API Service

API service for managing flights orders written on DRF

## Installing using GitHub

1. Clone the repository:
   ```bash
   git clone https://github.com/olenazaritska/airport-api-service.git

2. Navigate into the project directory:
   ```bash
   cd airport_api_service
   
3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   
4. Install the project requirements:
   ```bash
   pip install -r requirements.txt

5. Set environment variables:
   ```bash
   SECRET_KEY=<your-secret-key>
   DEBUG=<True/False>
   ALLOWED_HOSTS=<your-allowed-hosts>
   POSTGRES_PASSWORD=<your-postgres-password>
   POSTGRES_USER=<your-postgres-username>
   POSTGRES_DB=<your-postgres-database-name>
   POSTGRES_HOST=<your-postgres-host>
   POSTGRES_PORT=<your-postgres-port>
   PGDATA=<path-to-postgres-data-directory>
   
6. Apply database migrations
   ```bash
   python manage.py migrate

7. Run the development server:
   ```bash
   python manage.py runserver

## Run with Docker

1. Build the Docker images:
   ```bash
   docker-compose build
   
2. Start the containers:
   ```bash
   docker-compose up

## Getting Access

Creating a Superuser

* Locally: Run the following command to create a superuser:
   ```bash
   python manage.py createsuperuser

* From Docker container:
  1. Enter the container:
  ```bash
  docker exec -it <container_name> bash
  ```
  2. Create a superuser:
  ```bash
  python manage.py createsuperuser
  ```
  
##  Access for Regular Users
* To register a new user through the API, visit `/api/user/register`
* To obtain a token for authentication, use `/api/user/token`

## Features
* JWT Authentication
* Throttling
* Documentation at `/api/schema/swagger-ui`
* Manage orders and tickets
* View (authenticated) and create (admin only) airports, routes, crew members, airplanes, airplane types and flights
* Filter routes and flights
