/**
 * Onglet « Supports de cours » — upload PDF ≤ 5 Mo rattaché à la classe (US-26).
 */
import { useEffect, useState, type FormEvent } from 'react';
import { listDocuments, uploadDocument, type CourseDocument } from '@/api/classroom';
import { getApiErrorMessage } from '@/api/errors';
import PdfDocumentList from '@/components/PdfDocumentList';

const MAX_SIZE = 5 * 1024 * 1024;

export default function DocumentsTab({ classId }: { classId: number }) {
  const [documents, setDocuments] = useState<CourseDocument[] | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const load = () => {
    listDocuments(classId)
      .then(setDocuments)
      .catch((err) => setError(getApiErrorMessage(err, 'Impossible de charger les supports de cours.')));
  };

  useEffect(load, [classId]);

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Seuls les fichiers .pdf sont acceptés.');
      return;
    }
    if (file.size > MAX_SIZE) {
      setError('PDF trop volumineux (> 5 Mo).');
      return;
    }
    setUploading(true);
    try {
      await uploadDocument(classId, file);
      setFile(null);
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Échec de l’upload.'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleUpload} className="card flex gap-3 items-end flex-wrap">
        <div className="flex-1 min-w-[220px]">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Support de cours (PDF, ≤ 5 Mo)
          </label>
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="input"
          />
        </div>
        <button type="submit" disabled={!file || uploading} className="btn-primary">
          {uploading ? 'Envoi…' : '📎 Uploader'}
        </button>
      </form>

      {error && (
        <div className="p-3 bg-rose-50 border-l-4 border-rose-500 text-sm text-rose-900 rounded">{error}</div>
      )}

      {documents === null ? (
        <p className="text-slate-500">Chargement…</p>
      ) : documents.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-4xl mb-3">📄</div>
          <p className="text-slate-600">Aucun support de cours pour cette classe.</p>
        </div>
      ) : (
        <div className="card">
          <PdfDocumentList documents={documents} />
        </div>
      )}
    </div>
  );
}
