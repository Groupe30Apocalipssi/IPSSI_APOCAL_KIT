"""Sérialiseurs pour les endpoints LLM (génération de quiz)."""

from rest_framework import serializers

from .pdf_utils import MAX_PDF_SIZE_BYTES

MIN_SOURCE_TEXT_CHARS = 200


class GenerateQuizSerializer(serializers.Serializer):
    """Input pour POST /api/llm/generate-quiz/.

    Soit `pdf` (file) soit `source_text` (str ≥ 200 chars). Un des deux est
    requis.
    """

    title = serializers.CharField(max_length=200)
    pdf = serializers.FileField(required=False)
    source_text = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        pdf = attrs.get("pdf")
        source_text = (attrs.get("source_text") or "").strip()

        if not pdf and not source_text:
            raise serializers.ValidationError(
                "Fournir soit `pdf`, soit `source_text` (≥ 200 caractères)."
            )

        if pdf and source_text:
            raise serializers.ValidationError(
                "Choisir une seule source : un PDF ou un texte collé, pas les deux."
            )

        if not pdf and len(source_text) < MIN_SOURCE_TEXT_CHARS:
            raise serializers.ValidationError(
                {
                    "source_text": f"Doit faire au moins {MIN_SOURCE_TEXT_CHARS} caractères.",
                }
            )

        if pdf and not pdf.name.lower().endswith(".pdf"):
            raise serializers.ValidationError({"pdf": "Seuls les fichiers .pdf sont acceptés."})

        if pdf and getattr(pdf, "size", 0) > MAX_PDF_SIZE_BYTES:
            max_mb = MAX_PDF_SIZE_BYTES // (1024 * 1024)
            raise serializers.ValidationError({"pdf": f"PDF trop volumineux (> {max_mb} Mo)."})

        attrs["source_text"] = source_text
        return attrs
