"""
Modèles de l'app classroom — espace enseignant.

Une Classe appartient à un enseignant (`Profile.role == "teacher"`). Les
étudiants la rejoignent via un code court (`Classe.code`), à la manière de
Google Classroom : pas de gestion manuelle d'inscriptions par l'enseignant.

Les quiz assignés à une classe restent des `quizzes.Quiz` ordinaires (voir
`quizzes/models.py`) : un quiz « gabarit » (is_template=True) appartient à
l'enseignant, et chaque étudiant reçoit sa PROPRE copie (is_template=False,
source_quiz=gabarit) au moment de la publication. Cela réutilise tel quel
tout le code existant de passage/correction de quiz (aucune régression).
"""

import secrets
import string

from django.conf import settings
from django.db import models

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6


def _generate_class_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


class Classe(models.Model):
    """Une classe gérée par un enseignant."""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classes_enseignees",
        help_text="Enseignant propriétaire de la classe.",
    )
    name = models.CharField(max_length=120, help_text="Nom de la classe.")
    code = models.CharField(
        max_length=_CODE_LENGTH,
        unique=True,
        editable=False,
        help_text="Code que les étudiants saisissent pour rejoindre la classe.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            code = _generate_class_code()
            while Classe.objects.filter(code=code).exists():
                code = _generate_class_code()
            self.code = code
        super().save(*args, **kwargs)


class Enrollment(models.Model):
    """Inscription d'un étudiant à une classe."""

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("classe", "student")]
        ordering = ["-joined_at"]
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"

    def __str__(self) -> str:
        return f"{self.student} ∈ {self.classe}"


class CourseDocument(models.Model):
    """Support de cours (PDF) uploadé par l'enseignant et rattaché à une classe."""

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="course_documents/%Y/%m/")
    original_name = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Support de cours"
        verbose_name_plural = "Supports de cours"

    def __str__(self) -> str:
        return self.original_name
