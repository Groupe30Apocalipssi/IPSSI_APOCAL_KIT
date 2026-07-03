from django.urls import path

from .views import (
    AtRiskStudentsView,
    ClassDetailView,
    ClassDocumentsView,
    ClassListCreateView,
    ClassQuizDetailView,
    ClassQuizGenerateView,
    ClassQuizListView,
    ClassQuizPublishView,
    ClassQuizQuestionEditView,
    ClassQuizStatsView,
    ClassRosterView,
    JoinClassView,
    StudentDetailInClassView,
)

urlpatterns = [
    path("classes/", ClassListCreateView.as_view(), name="classroom-classes"),
    path("join/", JoinClassView.as_view(), name="classroom-join"),
    path("classes/<int:pk>/", ClassDetailView.as_view(), name="classroom-class-detail"),
    path("classes/<int:pk>/students/", ClassRosterView.as_view(), name="classroom-roster"),
    path(
        "classes/<int:pk>/students/<int:student_id>/",
        StudentDetailInClassView.as_view(),
        name="classroom-student-detail",
    ),
    path("classes/<int:pk>/at-risk/", AtRiskStudentsView.as_view(), name="classroom-at-risk"),
    path("classes/<int:pk>/documents/", ClassDocumentsView.as_view(), name="classroom-documents"),
    path("classes/<int:pk>/quizzes/", ClassQuizListView.as_view(), name="classroom-quizzes"),
    path(
        "classes/<int:pk>/quizzes/generate/",
        ClassQuizGenerateView.as_view(),
        name="classroom-quiz-generate",
    ),
    path(
        "classes/<int:pk>/quizzes/<int:quiz_id>/",
        ClassQuizDetailView.as_view(),
        name="classroom-quiz-detail",
    ),
    path(
        "classes/<int:pk>/quizzes/<int:quiz_id>/questions/<int:index>/",
        ClassQuizQuestionEditView.as_view(),
        name="classroom-quiz-question-edit",
    ),
    path(
        "classes/<int:pk>/quizzes/<int:quiz_id>/publish/",
        ClassQuizPublishView.as_view(),
        name="classroom-quiz-publish",
    ),
    path(
        "classes/<int:pk>/quizzes/<int:quiz_id>/stats/",
        ClassQuizStatsView.as_view(),
        name="classroom-quiz-stats",
    ),
]
