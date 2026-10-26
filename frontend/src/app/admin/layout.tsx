"use client";

import AuthHeader from "@/components/AuthHeader";
import ProtectedRoute from "@/components/ProtectedRoute";
import { AdminSessionProvider } from "@/contexts/AdminSessionContext";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute perfilPermitido="ADMIN">
      {(sessao) => (
        <AdminSessionProvider sessao={sessao}>
          <AuthHeader sessao={sessao} />
          {children}
        </AdminSessionProvider>
      )}
    </ProtectedRoute>
  );
}