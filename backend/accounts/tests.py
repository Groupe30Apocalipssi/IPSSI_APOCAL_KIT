"""Tests pédagogiques pour l'app accounts.

Ces tests servent d'exemples : signup, login, logout, accès protégé.
Lancez : pytest accounts/
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="alice@test.com", password="motdepasse123"
    )


def test_signup_creates_user(client):
    # Lot 3 : inscription par EMAIL (username = email en interne).
    response = client.post(
        "/api/accounts/signup/",
        {
            "email": "bob@test.com",
            "password": "motdepasse123",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert User.objects.filter(email="bob@test.com").exists()


def test_signup_requires_email(client):
    response = client.post(
        "/api/accounts/signup/",
        {"password": "motdepasse123"},
        format="json",
    )
    assert response.status_code == 400


def test_login_returns_token(client, user):
    response = client.post(
        "/api/accounts/login/",
        {"email": "alice@test.com", "password": "motdepasse123"},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert "token" in response.data
    assert response.data["user"]["email"] == "alice@test.com"


def test_login_with_wrong_password(client, user):
    response = client.post(
        "/api/accounts/login/",
        {"email": "alice@test.com", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 400


def test_me_requires_auth(client):
    response = client.get("/api/accounts/me/")
    assert response.status_code in (401, 403)


def test_me_with_token(client, user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.get("/api/accounts/me/")
    assert response.status_code == 200
    assert response.data["username"] == "alice"


def test_logout_invalidates_token(client, user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.post("/api/accounts/logout/")
    assert response.status_code == 204
    # Le token n'existe plus
    assert not Token.objects.filter(key=token.key).exists()


def test_export_requires_auth(client):
    response = client.get("/api/accounts/me/export/")
    assert response.status_code in (401, 403)


def test_export_success_json(client, user):
    from rest_framework.authtoken.models import Token
    from quizzes.models import Quiz
    from accounts.models import DataRequest
    import json

    # Création d'un quiz pour l'utilisateur
    Quiz.objects.create(user=user, title="Mon Quiz Test", source_text="Source test content", score=8)

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get("/api/accounts/me/export/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    
    data = json.loads(response.content.decode("utf-8"))
    assert "user" in data
    assert data["user"]["email"] == "alice@test.com"
    assert "quizzes" in data
    assert len(data["quizzes"]) == 1
    assert data["quizzes"][0]["title"] == "Mon Quiz Test"
    assert "signalements" in data
    assert "logs" in data

    # Vérification de l'audit trail
    assert DataRequest.objects.filter(user=user, status="completed").exists()


def test_export_strict_isolation(client, user):
    from rest_framework.authtoken.models import Token
    from django.contrib.auth.models import User
    from quizzes.models import Quiz
    import json

    # Utilisateur B et son quiz
    user_b = User.objects.create_user(username="bob", email="bob@test.com", password="pwd")
    Quiz.objects.create(user=user_b, title="Quiz de Bob", source_text="Bob's data", score=5)

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get("/api/accounts/me/export/")
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    
    # L'utilisateur A (Alice) ne doit pas voir les quiz de Bob
    assert len(data["quizzes"]) == 0


