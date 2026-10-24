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

-   Python 3.12+ (required by Django 6)
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

The response contains an `access` token and a `refresh` token.

Send the `access` token in the header of every request:

    Authorization: Bearer <access_token>

The access token is valid for 30 minutes. Get a new one with the
`refresh` token, which is valid for 1 day:

    POST /api/token/refresh/

Body:

    {
      "refresh": "your_refresh_token"
    }

------------------------------------------------------------------------

## Installation

### 1. Clone the Repository

    git clone https://github.com/mouquettom/softdesk-api.git

### 2. Navigate to the Project Directory

    cd softdesk-api

### 3. Create a Virtual Environment

#### macOS / Linux

    python3 -m venv venv
    source venv/bin/activate

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

## Running the Tests

The tests use Django REST Framework's `APITestCase`: no extra
dependency is needed. From the `src/` folder, with the virtual
environment activated:

    python manage.py test

To display the name of each test:

    python manage.py test -v 2

The tests live in `src/projects/tests.py` and check the three custom
permissions through the real endpoints:

| Permission           | What is tested                                                                 |
|----------------------|--------------------------------------------------------------------------------|
| `IsContributor`      | a non-contributor gets a 403 on every route of the project (read and write)    |
| `IsAuthorOrReadOnly` | a contributor can read, but only the author can update or delete a resource    |
| `IsProjectAuthor`    | only the project author can add or remove contributors                         |

They also cover JWT authentication (401 without a valid token) and the
rule that an issue can only be assigned to a project contributor.

------------------------------------------------------------------------

## Main Endpoints

All endpoints except registration and token creation require a JWT.

### Users

| Method   | Endpoint               | Description                    |
|----------|------------------------|--------------------------------|
| POST     | `/api/users/register/` | Create a user                  |
| GET      | `/api/users/me/`       | View your profile              |
| PATCH    | `/api/users/me/`       | Update your profile            |
| DELETE   | `/api/users/me/`       | Delete your account            |
| GET      | `/api/users/`          | List users (public profile)    |
| GET      | `/api/users/{id}/`     | View a user (public profile)   |
| DELETE   | `/api/users/{id}/`     | Delete a user (admin only)     |

Body to register:

    {
      "username": "your_username",
      "password": "your_password",
      "age": 25,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "can_be_contacted": false,
      "can_data_be_shared": false
    }

Only `username`, `password` (8 characters minimum) and `age` (15 minimum)
are required. The other fields are optional.

`PATCH /api/users/me/` accepts the same fields, except `age`.

------------------------------------------------------------------------

### Projects

| Method   | Endpoint              | Description                      |
|----------|-----------------------|----------------------------------|
| GET      | `/api/projects/`      | List your projects               |
| POST     | `/api/projects/`      | Create a project                 |
| GET      | `/api/projects/{id}/` | View a project                   |
| PATCH    | `/api/projects/{id}/` | Update a project (author only)   |
| DELETE   | `/api/projects/{id}/` | Delete a project (author only)   |

Body to create a project:

    {
      "title": "SoftDesk",
      "description": "Project description",
      "type": "back-end"
    }

`type` must be `back-end`, `front-end`, `iOS` or `Android`. The author
is the logged-in user, who is automatically added as a contributor.

------------------------------------------------------------------------

### Contributors

| Method   | Endpoint                                        | Description                                |
|----------|-------------------------------------------------|--------------------------------------------|
| GET      | `/api/projects/{project_id}/contributors/`      | List the contributors                      |
| POST     | `/api/projects/{project_id}/contributors/`      | Add a contributor (project author only)    |
| DELETE   | `/api/projects/{project_id}/contributors/{id}/` | Remove a contributor (project author only) |

Body to add a contributor (`user_id` is the id of the user to add):

    {
      "user_id": 2
    }

In `DELETE .../contributors/{id}/`, `{id}` is the `id` of the
contributor entry, as returned by `GET .../contributors/`. It is not
the user's id (the `user` field). The project author cannot be removed.

------------------------------------------------------------------------

### Issues

| Method   | Endpoint                                  | Description                     |
|----------|-------------------------------------------|---------------------------------|
| GET      | `/api/projects/{project_id}/issues/`      | List the issues of a project    |
| POST     | `/api/projects/{project_id}/issues/`      | Create an issue                 |
| GET      | `/api/projects/{project_id}/issues/{id}/` | View an issue                   |
| PATCH    | `/api/projects/{project_id}/issues/{id}/` | Update an issue (author only)   |
| DELETE   | `/api/projects/{project_id}/issues/{id}/` | Delete an issue (author only)   |

Body to create an issue:

    {
      "title": "Login bug",
      "description": "Users cannot log in",
      "priority": "HIGH",
      "tag": "BUG",
      "status": "To Do",
      "assignee_id": 2
    }

| Field         | Allowed values                     | Required               |
|---------------|------------------------------------|------------------------|
| `title`       | text, 128 characters maximum       | yes                    |
| `description` | text                               | yes                    |
| `priority`    | `LOW`, `MEDIUM`, `HIGH`            | yes                    |
| `tag`         | `BUG`, `FEATURE`, `TASK`           | yes                    |
| `status`      | `To Do`, `In Progress`, `Finished` | no (default: `To Do`)  |
| `assignee_id` | id of a user who is a contributor  | no                     |

------------------------------------------------------------------------

### Comments

| Method   | Endpoint                                                       | Description                      |
|----------|----------------------------------------------------------------|----------------------------------|
| GET      | `/api/projects/{project_id}/issues/{issue_id}/comments/`       | List the comments of an issue    |
| POST     | `/api/projects/{project_id}/issues/{issue_id}/comments/`       | Create a comment                 |
| GET      | `/api/projects/{project_id}/issues/{issue_id}/comments/{id}/`  | View a comment                   |
| PATCH    | `/api/projects/{project_id}/issues/{issue_id}/comments/{id}/`  | Update a comment (author only)   |
| DELETE   | `/api/projects/{project_id}/issues/{issue_id}/comments/{id}/`  | Delete a comment (author only)   |

Body to create a comment:

    {
      "description": "I'm looking into it"
    }

Comment ids are UUIDs, so `{id}` looks like
`3f6c1e2a-8b4d-4c1f-9a7e-2d5b6c8e9f01`.

------------------------------------------------------------------------

## Permissions

-   JWT authentication is required
-   only contributors can access projects (`IsContributor`)
-   only the author can update or delete their own content (`IsAuthorOrReadOnly`)
-   only the project author can manage contributors (`IsProjectAuthor`)
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
-   automated permission tests

------------------------------------------------------------------------

## Author

@tom_mouquet

Project developed as part of the OpenClassrooms **Développeur
d'application Python** training program.
