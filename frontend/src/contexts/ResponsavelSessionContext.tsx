
"use client";

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";

import type { Sessao } from "@/lib/auth";

const ResponsavelSessionContext =
  createContext<Sessao | null>(null);

interface ResponsavelSessionProviderProps {
  sessao: Sessao;
  children: ReactNode;
}

export function ResponsavelSessionProvider({
  sessao,
  children,
}: ResponsavelSessionProviderProps) {
  return (
    <ResponsavelSessionContext.Provider value={sessao}>
      {children}
    </ResponsavelSessionContext.Provider>
  );
}

export function useResponsavelSession(): Sessao {
  const sessao = useContext(ResponsavelSessionContext);

  if (!sessao) {
    throw new Error(
      "Sessão do responsável não disponível.",
    );
  }

  return sessao;
}
