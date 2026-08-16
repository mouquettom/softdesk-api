# SoftDesk API

Secure RESTful API developed with Django REST Framework as part of the
OpenClassrooms project **"Build a Secure RESTful API with Django
REST"**.

## Description

SoftDesk Support is a B2B API designed for collaborative technical 
project management:

-   user management
-   project creation
-   contributor management
-   issue/ticket tracking
-   comments on issues
-   secure JWT authentication

------------------------------------------------------------------------

## Technologies Used

-   Python 3
-   Django
-   Django REST Framework
-   Simple JWT
-   SQLite3

------------------------------------------------------------------------

## Project Structure

    src/
    ├── SoftDeskSupport/
    ├── users/
    ├── projects/
    ├── issues/
    └── comments/

------------------------------------------------------------------------

## Authentication

The API uses JWT (JSON Web Token) authentication.

## Obtain a Token

    POST /api/token/access/

Body:

    {
      "username": "your_username",
      "password": "your_password"
    }

------------------------------------------------------------------------

## Installation

### 1. Clone the Repository

    git clone https://github.com/mouquettom/softdesk-api.git

### 2. Navigate to the Project Directory

    cd softdesk-api

### 3. Create a Virtual Environment

#### macOS / Linux

    python3 -m venv .env
    source .env/bin/activate

#### Windows

    python -m venv venv
    venv\Scripts\activate

------------------------------------------------------------------------

### 4. Install Dependencies

    pip install -r requirements.txt

------------------------------------------------------------------------

### 5. Apply Migrations

    cd src
    python manage.py migrate

------------------------------------------------------------------------

### 6. Run the Server

    python manage.py runserver

------------------------------------------------------------------------

## Main Endpoints

### Users

  Method   Endpoint                 Description
  -------- ------------------------ ---------------------
  POST     `/api/users/register/`   Create a user
  GET      `/api/users/me/`         View your profile
  PATCH    `/api/users/me/`         Update your profile
  DELETE   `/api/users/me/`         Delete your account

------------------------------------------------------------------------

### Projects

  Method   Endpoint
  -------- -----------------------
  GET      `/api/projects/`
  POST     `/api/projects/`
  GET      `/api/projects/{id}/`
  PATCH    `/api/projects/{id}/`
  DELETE   `/api/projects/{id}/`

------------------------------------------------------------------------

### Contributors

  Method   Endpoint
  -------- -------------------------------------
  GET      `/api/projects/{project_id}/users/`
  POST     `/api/projects/{project_id}/users/`

------------------------------------------------------------------------

### Issues

  Method   Endpoint
  -------- --------------------------------------
  GET      `/api/projects/{project_id}/issues/`
  POST     `/api/projects/{project_id}/issues/`

------------------------------------------------------------------------

### Comments

  Method   Endpoint
  -------- ----------------------------------------------------------
  GET      `/api/projects/{project_id}/issues/{issue_id}/comments/`
  POST     `/api/projects/{project_id}/issues/{issue_id}/comments/`

------------------------------------------------------------------------

## Permissions

-   JWT authentication is required
-   only contributors can access projects
-   only the author can update or delete their own content
-   issues can only be assigned to project contributors

------------------------------------------------------------------------

## Technical Features

-   nested routes
-   custom permissions
-   DRF serializers
-   UUIDs for comments
-   business logic validation
-   pagination
-   custom user model

------------------------------------------------------------------------

## Author

@tom_mouquet

Project developed as part of the OpenClassrooms **Développeur
d'application Python** training program.
