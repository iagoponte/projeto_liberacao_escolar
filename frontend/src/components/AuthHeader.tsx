
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  fazerLogout,
  type Sessao,
} from "@/lib/auth";

interface AuthHeaderProps {
  sessao: Sessao;
}

export default function AuthHeader({
  sessao,
}: AuthHeaderProps) {
  const router = useRouter();

  const [saindo, setSaindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function sair() {
    if (saindo) return;

    setErro(null);
    setSaindo(true);

    try {
      await fazerLogout(sessao.csrf_token);

      router.replace("/login");
      router.refresh();
    } catch (falha) {
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível encerrar a sessão.",
      );
    } finally {
      setSaindo(false);
    }
  }

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
        flexWrap: "wrap",
        padding: "16px 24px",
        borderBottom: "1px solid #e5e7eb",
        backgroundColor: "#ffffff",
      }}
    >
      <div>
        <strong>Sistema de Liberação Escolar</strong>

        <p style={{ fontSize: "14px", color: "#526071" }}>
          {sessao.usuario.email} — {sessao.usuario.perfil}
        </p>
      </div>

      <div>
        <button
          type="button"
          disabled={saindo}
          onClick={sair}
          style={{
            padding: "10px 16px",
            border: "1px solid #cbd5e1",
            borderRadius: "6px",
            backgroundColor: "#ffffff",
            cursor: saindo ? "wait" : "pointer",
          }}
        >
          {saindo ? "Saindo..." : "Sair"}
        </button>

        {erro && (
          <p
            role="alert"
            style={{
              color: "#b42318",
              fontSize: "14px",
              marginTop: "8px",
            }}
          >
            {erro}
          </p>
        )}
      </div>
    </header>
  );
}
