
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import { fazerLogin } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviarFormulario(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (carregando) return;

    setErro(null);
    setCarregando(true);

    try {
      const sessao = await fazerLogin({
        email: email.trim(),
        senha,
      });

      if (sessao.usuario.perfil === "ADMIN") {
        router.push("/admin");
      } else {
        router.push("/responsavel");
      }
    } catch (falha) {
      if (falha instanceof ApiError && falha.status === 429) {
        setErro(
          "Muitas tentativas de acesso. Tente novamente mais tarde.",
        );
      } else if (falha instanceof ApiError && falha.status === 401) {
        setErro("Credenciais invalidas.");
      } else if (falha instanceof Error) {
        setErro(falha.message);
      } else {
        setErro("Não foi possível realizar o login.");
      }
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "24px",
        backgroundColor: "#f4f6f9",
      }}
    >
      <section
        style={{
          width: "100%",
          maxWidth: "420px",
          padding: "32px",
          backgroundColor: "#ffffff",
          borderRadius: "12px",
          boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
        }}
      >
        <h1
          style={{
            fontSize: "26px",
            fontWeight: 700,
            marginBottom: "8px",
            color: "#17233b",
          }}
        >
          Liberação Escolar
        </h1>

        <p style={{ marginBottom: "28px", color: "#526071" }}>
          Acesse sua conta para continuar.
        </p>

        <form onSubmit={enviarFormulario}>
          <div style={{ marginBottom: "16px" }}>
            <label
              htmlFor="email"
              style={{ display: "block", marginBottom: "6px" }}
            >
              Email
            </label>

            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(evento) => setEmail(evento.target.value)}
              style={{
                width: "100%",
                padding: "12px",
                border: "1px solid #aab4c0",
                borderRadius: "6px",
              }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label
              htmlFor="senha"
              style={{ display: "block", marginBottom: "6px" }}
            >
              Senha
            </label>

            <input
              id="senha"
              type="password"
              autoComplete="current-password"
              required
              value={senha}
              onChange={(evento) => setSenha(evento.target.value)}
              style={{
                width: "100%",
                padding: "12px",
                border: "1px solid #aab4c0",
                borderRadius: "6px",
              }}
            />
          </div>

          {erro && (
            <p
              role="alert"
              style={{
                color: "#b42318",
                marginBottom: "16px",
              }}
            >
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={carregando}
            style={{
              width: "100%",
              padding: "12px",
              backgroundColor: "#1d4ed8",
              color: "#ffffff",
              border: 0,
              borderRadius: "6px",
              cursor: carregando ? "wait" : "pointer",
              opacity: carregando ? 0.7 : 1,
            }}
          >
            {carregando ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}


