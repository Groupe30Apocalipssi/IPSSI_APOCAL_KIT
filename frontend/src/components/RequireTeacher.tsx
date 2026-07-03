import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { ReactNode } from 'react';

/**
 * Wrap une route réservée aux comptes ENSEIGNANT (Profile.role === "teacher").
 * - Pas connecté -> /login
 * - Connecté mais pas enseignant -> accueil (pas d'accès à l'espace enseignant)
 */
export default function RequireTeacher({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="text-center text-slate-500 py-12">Chargement…</div>;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (user.role !== 'teacher') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
