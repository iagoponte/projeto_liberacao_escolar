
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import {
  obterSessao,
  type Perfil,
  type Sessao,
} from "@/lib/auth";

interface ProtectedRouteProps {
  perfilPermitido: Perfil;
  children: React.ReactNode | ((sessao: Sessao) => React.ReactNode);
}

export default function ProtectedRoute({
  perfilPermitido,
  children,
}: ProtectedRouteProps) {
  const router = useRouter();

  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [verificando, setVerificando] = useState(true);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    let ativo = true;

    async function verificarSessao() {
      try {
        const resultado = await obterSessao();

        if (!ativo) return;

        if (resultado.usuario.perfil !== perfilPermitido) {
          router.replace(
            resultado.usuario.perfil === "ADMIN"
              ? "/admin"
              : "/responsavel",
          );
          return;
        }

        setSessao(resultado);
      } catch (falha) {
        if (!ativo) return;

        if (falha instanceof ApiError && falha.status === 401) {
          router.replace("/login");
        } else {
          setErro(true);
        }
      } finally {
        if (ativo) setVerificando(false);
      }
    }

    void verificarSessao();

    return () => {
      ativo = false;
    };
  }, [perfilPermitido, router]);

  if (erro) {
    return (
      <main role="alert">
        Não foi possível verificar sua sessão. Atualize a página.
      </main>
    );
  }

  if (verificando || !sessao) {
    return (
      <main aria-live="polite">
        Verificando sessão...
      </main>
    );
  }

  return (
  <>
    {typeof children === "function"
      ? children(sessao)
      : children}
  </>
);
}
