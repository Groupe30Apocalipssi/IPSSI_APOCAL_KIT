/**
 * Liste de supports de cours (PDF) avec aperçu intégré au clic (au lieu d'un
 * simple lien de téléchargement) — utilisée côté enseignant et côté étudiant.
 */
import { useState } from 'react';
import type { CourseDocument } from '@/api/classroom';

function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function PdfDocumentList({ documents }: { documents: CourseDocument[] }) {
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <ul className="divide-y divide-slate-100">
      {documents.map((d) => {
        const isOpen = openId === d.id;
        return (
          <li key={d.id} className="py-2">
            <div className="flex items-center justify-between gap-3 text-sm">
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : d.id)}
                className="text-indigo-600 hover:underline text-left flex items-center gap-2 min-w-0"
              >
                <span className="truncate">📄 {d.original_name}</span>
                <span className="text-xs text-slate-400 shrink-0">{isOpen ? '▲ masquer' : '▼ aperçu'}</span>
              </button>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-slate-500">{formatSize(d.size_bytes)}</span>
                <a
                  href={d.file}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-slate-500 hover:text-indigo-600"
                  title="Ouvrir dans un nouvel onglet"
                >
                  ⤢
                </a>
              </div>
            </div>
            {isOpen && (
              <iframe
                src={d.file}
                title={d.original_name}
                className="w-full h-[480px] mt-2 border border-slate-200 rounded"
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}
