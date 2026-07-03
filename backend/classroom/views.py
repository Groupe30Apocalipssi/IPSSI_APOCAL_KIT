"""
Endpoints de l'espace enseignant (classroom).

    POST   /api/classroom/classes/                              — créer une classe (enseignant)
    GET    /api/classroom/classes/                              — mes classes (enseignant) / classes rejointes (étudiant)
    GET    /api/classroom/classes/<id>/                          — détail d'une classe
    POST   /api/classroom/join/                                  — rejoindre une classe (étudiant, via code)

    GET    /api/classroom/classes/<id>/students/                 — liste des étudiants de la classe (roster)
    GET    /api/classroom/classes/<id>/students/<sid>/            — scores détaillés d'un étudiant
    GET    /api/classroom/classes/<id>/at-risk/                   — étudiants en difficulté

    GET    /api/classroom/classes/<id>/documents/                 — supports de cours de la classe
    POST   /api/classroom/classes/<id>/documents/                 — uploader un support (PDF ≤ 5 Mo)

    GET    /api/classroom/classes/<id>/quizzes/                   — quiz de la classe
    POST   /api/classroom/classes/<id>/quizzes/generate/           — générer un gabarit de 10 QCM (brouillon)
    GET    /api/classroom/classes/<id>/quizzes/<qid>/               — relecture d'un gabarit
    PATCH  /api/classroom/classes/<id>/quizzes/<qid>/questions/<i>/ — éditer une question du gabarit
    POST   /api/classroom/classes/<id>/quizzes/<qid>/publish/       — publier aux étudiants inscrits
    GET    /api/classroom/classes/<id>/quizzes/<qid>/stats/         — moyenne + % réussite par question
"""

import logging

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg, Count, F
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import get_or_create_profile
from llm.pdf_utils import MAX_PDF_SIZE_BYTES, PDFError, extract_text_from_pdf
from llm.services import get_llm_client
from llm.services.base import LLMError
from quizzes.models import Question, Quiz

from .models import Classe, CourseDocument, Enrollment
from .serializers import (
    ClasseCreateSerializer,
    ClasseSerializer,
    CourseDocumentSerializer,
    JoinClassSerializer,
    QuestionEditSerializer,
    TemplateQuizSerializer,
)

logger = logging.getLogger(__name__)


class IsTeacher(BasePermission):
    """Autorise uniquement les comptes dont le profil a le rôle « enseignant »."""

    message = "Réservé aux comptes enseignant."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and get_or_create_profile(request.user).is_teacher
        )


def _clone_quiz_for_student(template: Quiz, student: User) -> Quiz:
    """Copie un gabarit publié en un quiz personnel joué par `student`.

    Réutilise tel quel le modèle Quiz/Question existant (score, selected_index)
    -> aucune modification nécessaire du flux de passage/correction de quiz.
    """
    copy = Quiz.objects.create(
        user=student,
        title=template.title,
        source_text=template.source_text,
        classe=template.classe,
        status=Quiz.STATUS_PUBLISHED,
        is_template=False,
        source_quiz=template,
    )
    for q in template.questions.all():
        Question.objects.create(
            quiz=copy,
            index=q.index,
            prompt=q.prompt,
            options=q.options,
            correct_index=q.correct_index,
        )
    return copy


# ---------------------------------------------------------------------------
# Classes : création, liste, détail, rejoindre
# ---------------------------------------------------------------------------


class ClassListCreateView(APIView):
    """Classes de l'utilisateur : enseignées (enseignant) ou rejointes (étudiant)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ClasseSerializer(many=True)})
    def get(self, request):
        profile = get_or_create_profile(request.user)
        if profile.is_teacher:
            classes = Classe.objects.filter(teacher=request.user)
        else:
            classes = Classe.objects.filter(enrollments__student=request.user)
        return Response(ClasseSerializer(classes, many=True).data)

    @extend_schema(request=ClasseCreateSerializer, responses={201: ClasseSerializer})
    def post(self, request):
        if not get_or_create_profile(request.user).is_teacher:
            return Response(
                {"detail": "Réservé aux comptes enseignant."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = ClasseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        classe = Classe.objects.create(teacher=request.user, name=serializer.validated_data["name"])
        return Response(ClasseSerializer(classe).data, status=status.HTTP_201_CREATED)


class ClassDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_classe(self, request, pk: int) -> Classe:
        profile = get_or_create_profile(request.user)
        if profile.is_teacher:
            return get_object_or_404(Classe, pk=pk, teacher=request.user)
        return get_object_or_404(Classe, pk=pk, enrollments__student=request.user)

    @extend_schema(responses={200: ClasseSerializer})
    def get(self, request, pk: int):
        return Response(ClasseSerializer(self._get_classe(request, pk)).data)


class JoinClassView(APIView):
    """Un étudiant rejoint une classe via son code."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=JoinClassSerializer, responses={200: ClasseSerializer})
    def post(self, request):
        serializer = JoinClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        classe = Classe.objects.get(code=serializer.validated_data["code"])

        if classe.teacher_id == request.user.id:
            return Response(
                {"detail": "Vous êtes l'enseignant de cette classe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, created = Enrollment.objects.get_or_create(classe=classe, student=request.user)

        # Rattrapage : cloner les gabarits déjà publiés que l'étudiant n'a pas encore reçus.
        published_templates = classe.quizzes.filter(is_template=True, status=Quiz.STATUS_PUBLISHED)
        already_cloned_ids = set(
            Quiz.objects.filter(
                source_quiz__in=published_templates, user=request.user
            ).values_list("source_quiz_id", flat=True)
        )
        for template in published_templates:
            if template.id not in already_cloned_ids:
                _clone_quiz_for_student(template, request.user)

        return Response(
            ClasseSerializer(classe).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Roster, scores individuels, étudiants en difficulté
# ---------------------------------------------------------------------------


class ClassRosterView(APIView):
    """Liste des étudiants de la classe, avec leurs statistiques agrégées."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses={200: OpenApiResponse(description="Liste des étudiants + moyenne")})
    def get(self, request, pk: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        rows = []
        for enrollment in classe.enrollments.select_related("student").order_by("student__first_name"):
            student = enrollment.student
            student_quizzes = Quiz.objects.filter(classe=classe, user=student, is_template=False)
            taken = student_quizzes.filter(score__isnull=False)
            agg = taken.aggregate(avg=Avg("score"), nb=Count("id"))
            rows.append(
                {
                    "id": student.id,
                    "email": student.email,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "joined_at": enrollment.joined_at,
                    "quizzes_assigned": student_quizzes.count(),
                    "quizzes_taken": agg["nb"] or 0,
                    "average_score": round(agg["avg"], 1) if agg["avg"] is not None else None,
                }
            )
        return Response({"count": len(rows), "students": rows})


class StudentDetailInClassView(APIView):
    """Scores détaillés d'un étudiant particulier, au sein d'une classe."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses={200: OpenApiResponse(description="Scores détaillés d'un étudiant")})
    def get(self, request, pk: int, student_id: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        get_object_or_404(Enrollment, classe=classe, student_id=student_id)
        student = get_object_or_404(User, pk=student_id)

        quizzes = Quiz.objects.filter(classe=classe, user=student, is_template=False).order_by(
            "-created_at"
        )
        items = [
            {
                "quiz_id": q.id,
                "template_id": q.source_quiz_id,
                "title": q.title,
                "score": q.score,
                "created_at": q.created_at,
            }
            for q in quizzes
        ]
        agg = quizzes.filter(score__isnull=False).aggregate(avg=Avg("score"))
        return Response(
            {
                "student": {
                    "id": student.id,
                    "email": student.email,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                },
                "average_score": round(agg["avg"], 1) if agg["avg"] is not None else None,
                "quizzes": items,
            }
        )


class AtRiskStudentsView(APIView):
    """Étudiants en difficulté (moyenne < seuil, ou aucun quiz passé), triés du plus faible au plus fort."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses={200: OpenApiResponse(description="Étudiants en difficulté")})
    def get(self, request, pk: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        try:
            threshold = float(request.query_params.get("threshold", 5))
        except ValueError:
            threshold = 5.0

        rows = []
        for enrollment in classe.enrollments.select_related("student"):
            student = enrollment.student
            taken = Quiz.objects.filter(
                classe=classe, user=student, is_template=False, score__isnull=False
            )
            agg = taken.aggregate(avg=Avg("score"), nb=Count("id"))
            nb_taken = agg["nb"] or 0
            avg = round(agg["avg"], 1) if agg["avg"] is not None else None
            at_risk = nb_taken == 0 or (avg is not None and avg < threshold)
            if at_risk:
                rows.append(
                    {
                        "id": student.id,
                        "email": student.email,
                        "first_name": student.first_name,
                        "last_name": student.last_name,
                        "average_score": avg,
                        "quizzes_taken": nb_taken,
                        "reason": "Aucun quiz passé" if nb_taken == 0 else f"Moyenne < {threshold}/10",
                    }
                )
        rows.sort(key=lambda r: r["average_score"] if r["average_score"] is not None else -1)
        return Response({"threshold": threshold, "count": len(rows), "students": rows})


# ---------------------------------------------------------------------------
# Supports de cours (documents)
# ---------------------------------------------------------------------------


class ClassDocumentsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _get_classe_for_read(self, request, pk: int) -> Classe:
        profile = get_or_create_profile(request.user)
        if profile.is_teacher:
            return get_object_or_404(Classe, pk=pk, teacher=request.user)
        return get_object_or_404(Classe, pk=pk, enrollments__student=request.user)

    @extend_schema(responses={200: CourseDocumentSerializer(many=True)})
    def get(self, request, pk: int):
        classe = self._get_classe_for_read(request, pk)
        serializer = CourseDocumentSerializer(
            classe.documents.all(), many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(responses={201: CourseDocumentSerializer})
    def post(self, request, pk: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)  # upload réservé à l'enseignant
        pdf = request.FILES.get("file")
        if not pdf:
            return Response(
                {"detail": "Fichier PDF requis (champ `file`)."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not pdf.name.lower().endswith(".pdf"):
            return Response(
                {"detail": "Seuls les fichiers .pdf sont acceptés."}, status=status.HTTP_400_BAD_REQUEST
            )
        if pdf.size > MAX_PDF_SIZE_BYTES:
            return Response(
                {"detail": f"PDF trop volumineux (> {MAX_PDF_SIZE_BYTES // (1024 * 1024)} Mo)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        doc = CourseDocument.objects.create(
            classe=classe,
            file=pdf,
            original_name=pdf.name,
            size_bytes=pdf.size,
            uploaded_by=request.user,
        )
        serializer = CourseDocumentSerializer(doc, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Quiz de classe : génération, relecture, édition, publication, statistiques
# ---------------------------------------------------------------------------


class ClassQuizGenerateView(APIView):
    """Génère un gabarit de 10 QCM (brouillon) pour une classe, à partir d'un PDF ou d'un texte."""

    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses={201: TemplateQuizSerializer})
    def post(self, request, pk: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)

        title = (request.data.get("title") or "").strip()
        if not title:
            return Response({"detail": "Le titre est requis."}, status=status.HTTP_400_BAD_REQUEST)

        pdf_file = request.FILES.get("pdf")
        source_text = (request.data.get("source_text") or "").strip()
        if not pdf_file and len(source_text) < 200:
            return Response(
                {"detail": "Fournir soit `pdf`, soit `source_text` (≥ 200 caractères)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pdf_file:
            if not pdf_file.name.lower().endswith(".pdf"):
                return Response(
                    {"detail": "Seuls les fichiers .pdf sont acceptés."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                source_text = extract_text_from_pdf(pdf_file)
            except PDFError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            questions_data = get_llm_client().generate_quiz(source_text=source_text, title=title)
        except LLMError as exc:
            return Response(
                {"detail": f"Échec génération LLM : {exc}"}, status=status.HTTP_502_BAD_GATEWAY
            )

        with transaction.atomic():
            quiz = Quiz.objects.create(
                user=request.user,
                title=title,
                source_text=source_text,
                classe=classe,
                status=Quiz.STATUS_DRAFT,
                is_template=True,
            )
            for i, q in enumerate(questions_data, start=1):
                Question.objects.create(
                    quiz=quiz,
                    index=i,
                    prompt=q["prompt"],
                    options=q["options"],
                    correct_index=q["correct_index"],
                )
        return Response(TemplateQuizSerializer(quiz).data, status=status.HTTP_201_CREATED)


class ClassQuizListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TemplateQuizSerializer(many=True)})
    def get(self, request, pk: int):
        profile = get_or_create_profile(request.user)
        if profile.is_teacher:
            classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
            quizzes = classe.quizzes.filter(is_template=True)
        else:
            classe = get_object_or_404(Classe, pk=pk, enrollments__student=request.user)
            quizzes = classe.quizzes.filter(is_template=True, status=Quiz.STATUS_PUBLISHED)
        return Response(TemplateQuizSerializer(quizzes, many=True).data)


class ClassQuizDetailView(APIView):
    """Relecture d'un gabarit de quiz (avec les bonnes réponses) — enseignant uniquement."""

    permission_classes = [IsAuthenticated, IsTeacher]

    def _get_template(self, request, pk: int, quiz_id: int) -> Quiz:
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        return get_object_or_404(Quiz, pk=quiz_id, classe=classe, is_template=True)

    @extend_schema(responses={200: TemplateQuizSerializer})
    def get(self, request, pk: int, quiz_id: int):
        return Response(TemplateQuizSerializer(self._get_template(request, pk, quiz_id)).data)


class ClassQuizQuestionEditView(APIView):
    """Édite une question d'un gabarit encore en brouillon — enseignant uniquement."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(request=QuestionEditSerializer, responses={200: TemplateQuizSerializer})
    def patch(self, request, pk: int, quiz_id: int, index: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        template = get_object_or_404(Quiz, pk=quiz_id, classe=classe, is_template=True)
        if template.status != Quiz.STATUS_DRAFT:
            return Response(
                {"detail": "Ce quiz est déjà publié : il n'est plus modifiable."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        question = get_object_or_404(Question, quiz=template, index=index)

        serializer = QuestionEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "prompt" in data:
            question.prompt = data["prompt"]
        if "options" in data:
            question.options = data["options"]
        if "correct_index" in data:
            question.correct_index = data["correct_index"]
        question.save()

        return Response(TemplateQuizSerializer(template).data)


class ClassQuizPublishView(APIView):
    """Publie un gabarit : le fige et clone une copie pour chaque étudiant inscrit."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses={200: TemplateQuizSerializer})
    def post(self, request, pk: int, quiz_id: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        template = get_object_or_404(Quiz, pk=quiz_id, classe=classe, is_template=True)

        if template.status == Quiz.STATUS_PUBLISHED:
            return Response({"detail": "Ce quiz est déjà publié."}, status=status.HTTP_400_BAD_REQUEST)

        questions = list(template.questions.order_by("index"))
        if len(questions) != 10:
            return Response(
                {"detail": "Le quiz doit contenir exactement 10 questions pour être publié."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for q in questions:
            if not q.prompt.strip() or not isinstance(q.options, list) or len(q.options) != 4:
                return Response(
                    {"detail": f"Question {q.index} incomplète (énoncé ou 4 options manquants)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            template.status = Quiz.STATUS_PUBLISHED
            template.save(update_fields=["status"])
            for student in User.objects.filter(enrollments__classe=classe):
                _clone_quiz_for_student(template, student)

        return Response(TemplateQuizSerializer(template).data)


class ClassQuizStatsView(APIView):
    """Moyenne de classe + % de réussite par question, pour un quiz de la classe."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses={200: OpenApiResponse(description="Statistiques du quiz")})
    def get(self, request, pk: int, quiz_id: int):
        classe = get_object_or_404(Classe, pk=pk, teacher=request.user)
        template = get_object_or_404(Quiz, pk=quiz_id, classe=classe, is_template=True)

        copies = Quiz.objects.filter(source_quiz=template, is_template=False)
        taken = copies.filter(score__isnull=False)
        agg = taken.aggregate(avg=Avg("score"), nb=Count("id"))

        per_question = []
        for q in template.questions.order_by("index"):
            answered = Question.objects.filter(
                quiz__source_quiz=template,
                quiz__is_template=False,
                index=q.index,
                selected_index__isnull=False,
            )
            nb_answered = answered.count()
            nb_correct = answered.filter(selected_index=F("correct_index")).count()
            per_question.append(
                {
                    "index": q.index,
                    "prompt": q.prompt,
                    "answered": nb_answered,
                    "correct": nb_correct,
                    "success_rate": round(100 * nb_correct / nb_answered) if nb_answered else None,
                }
            )

        results = [
            {"student_id": copy.user_id, "student_email": copy.user.email, "score": copy.score}
            for copy in copies.select_related("user")
        ]

        return Response(
            {
                "quiz_id": template.id,
                "title": template.title,
                "assigned": copies.count(),
                "taken": agg["nb"] or 0,
                "average_score": round(agg["avg"], 1) if agg["avg"] is not None else None,
                "per_question": per_question,
                "results": results,
            }
        )
