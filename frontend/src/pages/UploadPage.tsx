import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateQuiz } from '@/api/llm';
import { getApiErrorMessage } from '@/api/errors';

const MIN_SOURCE_TEXT_CHARS = 200;
const MAX_PDF_SIZE_BYTES = 5 * 1024 * 1024;
const MAX_PDF_SIZE_MB = MAX_PDF_SIZE_BYTES / (1024 * 1024);

export default function UploadPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<'pdf' | 'text'>('text');
  const [pdf, setPdf] = useState<File | null>(null);
  const [sourceText, setSourceText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const textLength = sourceText.trim().length;
  const pdfTooLarge = pdf ? pdf.size > MAX_PDF_SIZE_BYTES : false;
  const canSubmit =
    title.trim().length > 0 &&
    (mode === 'text' ? textLength >= MIN_SOURCE_TEXT_CHARS : !!pdf && !pdfTooLarge) &&
    !loading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'text' && textLength < MIN_SOURCE_TEXT_CHARS) {
      setError(`Le texte doit faire au moins ${MIN_SOURCE_TEXT_CHARS} caractères.`);
      return;
    }
    if (mode === 'pdf' && !pdf) {
      setError('Sélectionnez un fichier PDF.');
      return;
    }
    if (pdfTooLarge) {
      setError(`Le PDF doit faire ${MAX_PDF_SIZE_MB} Mo maximum.`);
      return;
    }

    setLoading(true);
    try {
      const quiz = await generateQuiz({
        title,
        pdf: mode === 'pdf' ? (pdf ?? undefined) : undefined,
        source_text: mode === 'text' ? sourceText : undefined,
      });
      navigate(`/quiz/${quiz.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Échec de la génération.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-2">Créer un nouveau quiz</h1>
      <p className="text-slate-600 mb-6">
        Uploade un PDF ou colle un texte. EduTutor IA génère 10 questions QCM.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-rose-50 border-l-4 border-rose-500 text-sm text-rose-900 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Titre du cours</label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex. Histoire — Révolution française"
            className="input"
          />
        </div>

        <div>
          <div className="flex gap-2 mb-3">
            <button
              type="button"
              onClick={() => {
                setMode('text');
                setError(null);
              }}
              className={`px-3 py-1 rounded text-sm font-medium ${
                mode === 'text'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              📝 Texte collé
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('pdf');
                setError(null);
              }}
              className={`px-3 py-1 rounded text-sm font-medium ${
                mode === 'pdf'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              📄 PDF
            </button>
          </div>

          {mode === 'text' ? (
            <textarea
              required
              rows={10}
              minLength={MIN_SOURCE_TEXT_CHARS}
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Collez ici le texte de votre cours (au moins 200 caractères)…"
              className="input"
            />
          ) : (
            <input
              type="file"
              accept=".pdf,application/pdf"
              required
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null;
                setPdf(file);
                setError(
                  file && file.size > MAX_PDF_SIZE_BYTES
                    ? `Le PDF doit faire ${MAX_PDF_SIZE_MB} Mo maximum.`
                    : null,
                );
              }}
              className="input"
            />
          )}
          {mode === 'text' && (
            <p className="text-xs text-slate-500 mt-1">
              {textLength} / {MIN_SOURCE_TEXT_CHARS} caractères minimum
            </p>
          )}
          {mode === 'pdf' && (
            <p className={`text-xs mt-1 ${pdfTooLarge ? 'text-rose-600' : 'text-slate-500'}`}>
              {pdf
                ? `${pdf.name} · ${(pdf.size / (1024 * 1024)).toFixed(1)} Mo`
                : `PDF texte uniquement, ${MAX_PDF_SIZE_MB} Mo maximum. Les PDF scannés sans texte ne sont pas pris en charge.`}
            </p>
          )}
        </div>

        <button type="submit" disabled={!canSubmit} className="btn-primary w-full">
          {loading ? (
            <>
              <span className="animate-spin">⏳</span> Génération en cours… (1 à 5 min sur CPU,
              patientez)
            </>
          ) : (
            <>🚀 Générer le quiz</>
          )}
        </button>

        <p className="text-xs text-slate-500 text-center">
          La génération peut prendre de 1 à 5 minutes selon votre machine (bien plus rapide avec un
          GPU ou un modèle plus léger).
        </p>
      </form>
    </div>
  );
}
