"""Benchmark de latence pour la generation de quiz par LLM."""

from pathlib import Path
from statistics import mean
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from llm.services import get_llm_client
from llm.services.factory import resolve_active


DEFAULT_SOURCE_TEXT = (
    "Le protocole HTTP permet a un client web de demander des ressources a un serveur. "
    "Une requete contient une methode comme GET ou POST, une URL, des en-tetes et parfois "
    "un corps. Le serveur renvoie une reponse avec un code de statut, par exemple 200 pour "
    "un succes ou 404 lorsque la ressource est introuvable. Les cookies et les jetons "
    "d'authentification servent a maintenir une session ou a identifier l'utilisateur. "
    "Dans une application web moderne, le frontend appelle souvent une API REST qui renvoie "
    "du JSON. Les tests doivent verifier les cas nominaux, les erreurs et les limites de "
    "securite pour eviter les regressions."
)


class Command(BaseCommand):
    help = "Mesure la latence LLM et valide le seuil de generation d'un quiz."

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold",
            type=float,
            default=60.0,
            help="Seuil maximal autorise en secondes pour une generation.",
        )
        parser.add_argument(
            "--repeat",
            type=int,
            default=1,
            help="Nombre de generations a mesurer.",
        )
        parser.add_argument(
            "--source-file",
            type=Path,
            default=None,
            help="Fichier texte de cours a utiliser au lieu du scenario par defaut.",
        )
        parser.add_argument(
            "--title",
            default="Benchmark LLM",
            help="Titre transmis au generateur de quiz.",
        )

    def handle(self, *args, **options):
        threshold = float(options["threshold"])
        repeat = max(1, int(options["repeat"]))
        source_text = self._load_source(options["source_file"])

        conf = resolve_active()
        timeout_label = f"{conf['timeout']}s" if conf["timeout"] else "(default)"
        self.stdout.write(
            "Backend: {backend} | Model: {model} | Timeout: {timeout}".format(
                backend=conf["backend"],
                model=conf["model"] or "(default)",
                timeout=timeout_label,
            )
        )

        client = get_llm_client()
        durations: list[float] = []

        for index in range(1, repeat + 1):
            started = perf_counter()
            questions = client.generate_quiz(source_text=source_text, title=options["title"])
            elapsed = perf_counter() - started

            if len(questions) != 10:
                raise CommandError(
                    f"Generation invalide: {len(questions)} questions au lieu de 10."
                )

            durations.append(elapsed)
            self.stdout.write(f"Run {index}/{repeat}: {elapsed:.2f}s - 10 questions")

        avg_duration = mean(durations)
        max_duration = max(durations)
        summary = (
            f"average={avg_duration:.2f}s max={max_duration:.2f}s "
            f"threshold={threshold:.2f}s"
        )

        if max_duration > threshold:
            raise CommandError(f"FAIL - performance LLM insuffisante ({summary})")

        self.stdout.write(self.style.SUCCESS(f"PASS - performance LLM validee ({summary})"))

    def _load_source(self, source_file: Path | None) -> str:
        if source_file is None:
            return DEFAULT_SOURCE_TEXT

        if not source_file.exists():
            raise CommandError(f"Fichier introuvable: {source_file}")

        source_text = source_file.read_text(encoding="utf-8").strip()
        if len(source_text) < 200:
            raise CommandError("Le fichier de benchmark doit contenir au moins 200 caracteres.")
        return source_text
