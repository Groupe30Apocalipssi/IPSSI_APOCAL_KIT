"""Tests pour l'app llm — K1 (ping) + K2 (generate-quiz)."""

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from quizzes.models import Quiz

pytestmark = pytest.mark.django_db


def make_text_pdf(text: str) -> bytes:
    """Construit un petit PDF texte sans dépendance de génération externe."""
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


@pytest.fixture
def auth_client() -> APIClient:
    user = User.objects.create_user(username="alice", password="motdepasse123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(LLM_BACKEND="mock")
def test_ping_in_mock_mode():
    response = APIClient().get("/api/llm/ping/")
    assert response.status_code == 200
    assert response.data["backend"] == "mock"


@override_settings(LLM_BACKEND="mock")
def test_generate_quiz_with_text(auth_client):
    response = auth_client.post(
        "/api/llm/generate-quiz/",
        {
            "title": "Mon cours de test",
            "source_text": "Lorem ipsum " * 50,
        },
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert response.data["title"] == "Mon cours de test"
    assert len(response.data["questions"]) == 10
    assert "correct_index" not in response.data["questions"][0]
    assert Quiz.objects.filter(title="Mon cours de test").count() == 1


@override_settings(LLM_BACKEND="mock")
def test_generate_quiz_with_pdf(auth_client):
    source = (
        "Le product backlog est une liste ordonnee de besoins produit. "
        "Le sprint planning selectionne les elements prioritaires. "
        "La sprint review inspecte l increment avec les parties prenantes. "
        "La definition of done fixe les criteres de qualite partages."
    )
    pdf = SimpleUploadedFile(
        "cours-agile.pdf",
        make_text_pdf(source),
        content_type="application/pdf",
    )
    response = auth_client.post(
        "/api/llm/generate-quiz/",
        {"title": "Cours PDF agile", "pdf": pdf},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert response.data["title"] == "Cours PDF agile"
    assert len(response.data["questions"]) == 10
    assert "correct_index" not in response.data["questions"][0]
    quiz = Quiz.objects.get(title="Cours PDF agile")
    assert "product backlog" in quiz.source_text.lower()


@override_settings(LLM_BACKEND="mock")
def test_generate_quiz_requires_text_or_pdf(auth_client):
    response = auth_client.post(
        "/api/llm/generate-quiz/",
        {"title": "Sans contenu"},
        format="multipart",
    )
    assert response.status_code == 400


@override_settings(LLM_BACKEND="mock")
def test_generate_quiz_rejects_short_text(auth_client):
    response = auth_client.post(
        "/api/llm/generate-quiz/",
        {"title": "Trop court", "source_text": "Court"},
        format="multipart",
    )
    assert response.status_code == 400


def test_generate_quiz_requires_auth():
    response = APIClient().post(
        "/api/llm/generate-quiz/",
        {"title": "X", "source_text": "x" * 200},
        format="multipart",
    )
    assert response.status_code in (401, 403)
