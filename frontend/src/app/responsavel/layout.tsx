"use client";

import AuthHeader from "@/components/AuthHeader";
import ProtectedRoute from "@/components/ProtectedRoute";

import {
  ResponsavelSessionProvider,
} from "@/contexts/ResponsavelSessionContext";

export default function ResponsavelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute perfilPermitido="RESPONSAVEL">
      {(sessao) => (
        <ResponsavelSessionProvider sessao={sessao}>
          <AuthHeader sessao={sessao} />
          {children}
        </ResponsavelSessionProvider>
      )}
    </ProtectedRoute>
  );
}