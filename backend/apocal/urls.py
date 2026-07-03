"""URLs racine du projet APOCAL'IPSSI."""

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from administration.views import PublicSiteConfigView


def health(_request):
    """Endpoint trivial pour les healthchecks externes."""
    return JsonResponse({"status": "ok", "service": "apocal-backend"})


# Sert les fichiers uploadés (supports de cours PDF). `xframe_options_exempt`
# retire le header X-Frame-Options ajouté par défaut par SecurityMiddleware :
# sans ça, le navigateur refuse d'afficher le PDF dans l'aperçu <iframe> du
# frontend (origine différente en dev : :3000 vs :8000).
media_serve = xframe_options_exempt(serve)


urlpatterns = [
    # Health
    path("health/", health, name="health"),
    # Admin Django (utile en dev)
    path("admin/", admin.site.urls),
    # API — apps métier
    path("api/accounts/", include("accounts.urls")),
    path("api/llm/", include("llm.urls")),
    path("api/quizzes/", include("quizzes.urls")),
    # API — administration (config site/LLM, users, opérations base)
    path("api/admin/", include("administration.urls")),
    path("api/site-config/", PublicSiteConfigView.as_view(), name="public-site-config"),
    # API — espace enseignant (classes, roster, documents, quiz)
    path("api/classroom/", include("classroom.urls")),
    # OpenAPI schema + Swagger UI + Redoc
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Supports de cours uploadés (dev ET prod — Caddy route /media/* vers ce
    # service en prod, voir Caddyfile). Pas de `static()` helper Django car il
    # est no-op hors DEBUG.
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]
