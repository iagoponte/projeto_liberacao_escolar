"use client";

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";

import type { Sessao } from "@/lib/auth";

const AdminSessionContext = createContext<Sessao | null>(null);

interface AdminSessionProviderProps {
  sessao: Sessao;
  children: ReactNode;
}

export function AdminSessionProvider({
  sessao,
  children,
}: AdminSessionProviderProps) {
  return (
    <AdminSessionContext.Provider value={sessao}>
      {children}
    </AdminSessionContext.Provider>
  );
}

export function useAdminSession(): Sessao {
  const sessao = useContext(AdminSessionContext);

  if (!sessao) {
    throw new Error(
      "Sessão administrativa não disponível.",
    );
  }

  return sessao;
}