"""Sérialiseurs de l'app classroom (espace enseignant)."""

from rest_framework import serializers

from quizzes.models import Quiz
from quizzes.serializers import QuestionSerializer

from .models import Classe, CourseDocument


class ClasseSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Classe
        fields = ["id", "name", "code", "created_at", "students_count"]
        read_only_fields = ["id", "code", "created_at", "students_count"]

    def get_students_count(self, obj: Classe) -> int:
        return obj.enrollments.count()


class ClasseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classe
        fields = ["name"]


class JoinClassSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        if not Classe.objects.filter(code=value).exists():
            raise serializers.ValidationError("Code de classe invalide.")
        return value


class CourseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseDocument
        fields = ["id", "original_name", "size_bytes", "uploaded_at", "file"]
        read_only_fields = fields


class TemplateQuizSerializer(serializers.ModelSerializer):
    """Gabarit de quiz enseignant — inclut les bonnes réponses (relecture)."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "status", "created_at", "questions"]
        read_only_fields = ["id", "status", "created_at", "questions"]


class QuestionEditSerializer(serializers.Serializer):
    """Édition partielle d'une question d'un gabarit (encore en brouillon)."""

    prompt = serializers.CharField(required=False, allow_blank=False)
    options = serializers.ListField(
        child=serializers.CharField(allow_blank=False), required=False
    )
    correct_index = serializers.IntegerField(required=False, min_value=0, max_value=3)

    def validate_options(self, value: list[str]) -> list[str]:
        if len(value) != 4:
            raise serializers.ValidationError("Exactement 4 options sont attendues.")
        return value

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("Aucun champ à modifier.")
        return attrs
