"""
Modèles de l'app accounts.

[Note pédagogique] On garde le modèle User standard de Django (simple et
robuste), et on lui ajoute un Profil 1-pour-1 pour les infos métier qui ne sont
pas dans User — ici `email_verified` (l'utilisateur a-t-il cliqué le lien de
confirmation envoyé par email ?).

Choix d'architecture « email = identifiant » : à l'inscription, on met
username = email (voir SignupSerializer). Le login se fait donc par email, sans
backend d'authentification custom. C'est le compromis le plus simple pour un
kit pédagogique (un vrai produit utiliserait souvent un User personnalisé avec
USERNAME_FIELD = 'email').
"""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Informations complémentaires attachées à un utilisateur."""

    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Étudiant"),
        (ROLE_TEACHER, "Enseignant"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # Validation "soft" : le compte fonctionne même si l'email n'est pas vérifié,
    # mais un bandeau invite l'utilisateur à cliquer le lien de confirmation.
    email_verified = models.BooleanField(default=False)
    # Rôle choisi à l'inscription : distingue l'espace « enseignant » (gestion
    # de classes) de l'espace « étudiant » (par défaut, comportement inchangé).
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email or self.user.username}>"

    @property
    def is_teacher(self) -> bool:
        return self.role == self.ROLE_TEACHER


def get_or_create_profile(user) -> Profile:
    """Récupère (ou crée) le profil d'un utilisateur.

    Pratique pour les comptes créés AVANT l'ajout du modèle Profile (ils n'ont
    pas encore de profil) : on le crée à la volée plutôt que de planter.
    """
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


class DataRequest(models.Model):
    """Enregistrement d'audit pour les demandes d'accès aux données (SAR) RGPD."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_requests",
        help_text="Utilisateur ayant formulé la demande."
    )
    requested_at = models.DateTimeField(auto_now_add=True, help_text="Date et heure de la demande.")
    status = models.CharField(
        max_length=20,
        choices=[
            ("received", "Reçue"),
            ("in_progress", "En cours"),
            ("completed", "Répondue"),
        ],
        default="received",
        help_text="Statut de traitement du SAR."
    )
    answered_at = models.DateTimeField(null=True, blank=True, help_text="Date et heure de réponse.")
    export_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 du fichier ou contenu exporté."
    )

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "Demande de données (SAR)"
        verbose_name_plural = "Demandes de données (SAR)"

    def __str__(self) -> str:
        return f"SAR<{self.user.email or self.user.username}> - {self.status}"

