
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import { useAdminSession } from "@/contexts/AdminSessionContext";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  criarResponsavelAdmin,
  listarResponsaveisAdmin,
  type ResponsavelAdmin,
} from "@/lib/responsaveis-admin";

export default function ResponsaveisAdminPage() {
  const { csrf_token } = useAdminSession();
  const { replace } = useRouter();

  const [responsaveis, setResponsaveis] =
    useState<ResponsavelAdmin[]>([]);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [sessaoExpirada, setSessaoExpirada] =
    useState(false);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(
    null,
  );

  const tratarErro = useCallback(
    (falha: unknown) => {
      const tipo = classificarErroHttp(falha);

      if (tipo === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        replace("/login");
        return;
      }

      if (tipo === "ACESSO_NEGADO") {
        setErro(
          "Você não possui permissão para esta operação.",
        );
        return;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível realizar a operação.",
      );
    },
    [replace],
  );

  useEffect(() => {
    let ativo = true;

    async function carregar() {
      try {
        const dados = await listarResponsaveisAdmin();

        if (ativo) setResponsaveis(dados);
      } catch (falha) {
        if (ativo) tratarErro(falha);
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    void carregar();

    return () => {
      ativo = false;
    };
  }, [tratarErro]);

  async function cadastrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (salvando) return;

    if (nome.trim().length === 0) {
      setErro("Informe o nome completo.");
      return;
    }

    if (senha.length < 12) {
      setErro("A senha deve possuir pelo menos 12 caracteres.");
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const novo = await criarResponsavelAdmin(
        {
          nome_completo: nome.trim(),
          email: email.trim().toLowerCase(),
          senha,
        },
        csrf_token,
      );

      setResponsaveis((atuais) =>
        [...atuais, novo].sort((a, b) =>
          a.nome_completo.localeCompare(
            b.nome_completo,
            "pt-BR",
          ),
        ),
      );

      setNome("");
      setEmail("");
      setSenha("");

      setSucesso(
        "Responsável cadastrado com sucesso.",
      );
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  if (sessaoExpirada) {
    return (
      <main role="status">
        Sessão expirada. Redirecionando para o login...
      </main>
    );
  }

  return (
    <main
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "32px",
      }}
    >
      <Link href="/admin">Voltar ao painel</Link>

      <h1>Gestão de responsáveis</h1>
      <p>
        Cadastre os responsáveis que poderão acessar o
        sistema escolar.
      </p>

      {erro && <p role="alert">{erro}</p>}
      {sucesso && <p role="status">{sucesso}</p>}

      <section
        aria-label="Cadastro de responsável"
        style={{
          border: "1px solid #cbd5e1",
          borderRadius: "8px",
          padding: "20px",
          marginTop: "24px",
        }}
      >
        <h2>Cadastrar responsável</h2>

        <form onSubmit={(evento) => void cadastrar(evento)}>
          <div>
            <label htmlFor="nome-responsavel">
              Nome completo
            </label>
            <input
              id="nome-responsavel"
              required
              maxLength={200}
              value={nome}
              onChange={(evento) =>
                setNome(evento.target.value)
              }
            />
          </div>

          <div style={{ marginTop: "12px" }}>
            <label htmlFor="email-responsavel">
              E-mail
            </label>
            <input
              id="email-responsavel"
              type="email"
              required
              maxLength={254}
              autoComplete="off"
              value={email}
              onChange={(evento) =>
                setEmail(evento.target.value)
              }
            />
          </div>

          <div style={{ marginTop: "12px" }}>
            <label htmlFor="senha-responsavel">
              Senha inicial (mínimo 12 caracteres)
            </label>
            <input
              id="senha-responsavel"
              type="password"
              minLength={12}
              maxLength={128}
              required
              autoComplete="new-password"
              value={senha}
              onChange={(evento) =>
                setSenha(evento.target.value)
              }
            />
          </div>

          <button
            type="submit"
            disabled={salvando}
            style={{ marginTop: "16px" }}
          >
            {salvando
              ? "Cadastrando..."
              : "Cadastrar responsável"}
          </button>
        </form>
      </section>

      <section
        aria-label="Responsáveis cadastrados"
        style={{ marginTop: "32px" }}
      >
        <h2>Responsáveis cadastrados</h2>

        {carregando ? (
          <p role="status">Carregando responsáveis...</p>
        ) : responsaveis.length === 0 ? (
          <p>Nenhum responsável cadastrado.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                textAlign: "left",
                borderCollapse: "collapse",
              }}
            >
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">E-mail</th>
                  <th scope="col">Situação</th>
                </tr>
              </thead>

              <tbody>
                {responsaveis.map((responsavel) => (
                  <tr key={responsavel.id}>
                    <td>{responsavel.nome_completo}</td>
                    <td>{responsavel.email}</td>
                    <td>
                      {responsavel.ativo &&
                      responsavel.usuario_ativo
                        ? "Ativo"
                        : "Inativo"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
