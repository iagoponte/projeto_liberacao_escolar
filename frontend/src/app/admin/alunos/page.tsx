
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { useAdminSession } from "@/contexts/AdminSessionContext";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  listarAlunosAdmin,
  criarAlunoAdmin,
  atualizarAlunoAdmin,
  type AlunoAdmin,
} from "@/lib/alunos-admin";

type FormularioAluno = {
  nome: string;
  matricula: string;
};

const formularioVazio: FormularioAluno = {
  nome: "",
  matricula: "",
};

export default function AlunosAdminPage() {
  const sessao = useAdminSession();
  const router = useRouter();

  const [alunos, setAlunos] = useState<AlunoAdmin[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);

  const [editando, setEditando] = useState<number | null>(null);
  const [formulario, setFormulario] =
    useState<FormularioAluno>(formularioVazio);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);

  const tratarErro = useCallback(
    (falha: unknown) => {
      const tipo = classificarErroHttp(falha);

      if (tipo === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        router.replace("/login");
        return;
      }

      if (tipo === "ACESSO_NEGADO") {
        setErro("Você não possui permissão para esta operação.");
        return;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível realizar a operação.",
      );
    },
    [router],
  );

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);

    try {
      const resultado = await listarAlunosAdmin();
      setAlunos(resultado);
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setCarregando(false);
    }
  }, [tratarErro]);

  useEffect(() => {
    let ativo = true;

    async function iniciar() {
      try {
        const resultado = await listarAlunosAdmin();
        if (ativo) setAlunos(resultado);
      } catch (falha) {
        if (ativo) tratarErro(falha);
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    void iniciar();

    return () => {
      ativo = false;
    };
  }, [tratarErro]);

  function iniciarEdicao(aluno: AlunoAdmin) {
    setEditando(aluno.id);
    setFormulario({
      nome: aluno.nome_completo,
      matricula: aluno.matricula_institucional ?? "",
    });
    setErro(null);
    setSucesso(null);
  }

  function cancelarEdicao() {
    setEditando(null);
    setFormulario(formularioVazio);
    setErro(null);
  }

  async function salvar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (salvando) return;

    const nome = formulario.nome.trim();

    if (!nome || nome.length > 200) {
      setErro("Informe um nome válido de até 200 caracteres.");
      return;
    }

    const dados = {
      nome_completo: nome,
      matricula_institucional:
        formulario.matricula.trim() || null,
    };

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const resultado =
        editando === null
          ? await criarAlunoAdmin(dados, sessao.csrf_token)
          : await atualizarAlunoAdmin(
              editando,
              dados,
              sessao.csrf_token,
            );

      // O POST/PATCH já confirmou a persistência.
      setAlunos((atuais) => {
        const semRegistro = atuais.filter(
          (aluno) => aluno.id !== resultado.id,
        );

        return [...semRegistro, resultado].sort(
          (a, b) => a.id - b.id,
        );
      });

      setSucesso(
        editando === null
          ? "Aluno cadastrado com sucesso."
          : "Aluno atualizado com sucesso.",
      );

      setEditando(null);
      setFormulario(formularioVazio);
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  async function alterarSituacao(aluno: AlunoAdmin) {
    if (salvando) return;

    const acao = aluno.ativo ? "desativar" : "reativar";

    if (
      !window.confirm(
        `Deseja ${acao} o cadastro de ${aluno.nome_completo}?`,
      )
    ) {
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const atualizado = await atualizarAlunoAdmin(
        aluno.id,
        { ativo: !aluno.ativo },
        sessao.csrf_token,
      );

      setAlunos((atuais) =>
        atuais.map((item) =>
          item.id === atualizado.id ? atualizado : item,
        ),
      );

      setSucesso("Situação do aluno atualizada.");
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

      <h1>Gestão de alunos</h1>
      <p>Cadastre e gerencie os alunos da escola.</p>

      {erro && <p role="alert">{erro}</p>}
      {sucesso && <p role="status">{sucesso}</p>}

      <section
        aria-label="Formulário de aluno"
        style={{
          marginTop: "24px",
          marginBottom: "32px",
          padding: "20px",
          border: "1px solid #cbd5e1",
          borderRadius: "8px",
        }}
      >
        <h2>
          {editando === null
            ? "Cadastrar aluno"
            : "Editar aluno"}
        </h2>

        <form onSubmit={(evento) => void salvar(evento)}>
          <div>
            <label htmlFor="nome-aluno">
              Nome completo
            </label>

            <input
              id="nome-aluno"
              required
              maxLength={200}
              value={formulario.nome}
              onChange={(evento) =>
                setFormulario((atual) => ({
                  ...atual,
                  nome: evento.target.value,
                }))
              }
            />
          </div>

          <div style={{ marginTop: "12px" }}>
            <label htmlFor="matricula-aluno">
              Matrícula institucional (opcional)
            </label>

            <input
              id="matricula-aluno"
              value={formulario.matricula}
              onChange={(evento) =>
                setFormulario((atual) => ({
                  ...atual,
                  matricula: evento.target.value,
                }))
              }
            />
          </div>

          <div
            style={{
              display: "flex",
              gap: "12px",
              marginTop: "16px",
            }}
          >
            <button type="submit" disabled={salvando}>
              {salvando
                ? "Salvando..."
                : editando === null
                  ? "Cadastrar"
                  : "Salvar alterações"}
            </button>

            {editando !== null && (
              <button
                type="button"
                disabled={salvando}
                onClick={cancelarEdicao}
              >
                Cancelar edição
              </button>
            )}
          </div>
        </form>
      </section>

      <section aria-label="Alunos cadastrados">
        <h2>Alunos cadastrados</h2>

        <button
          type="button"
          disabled={carregando || salvando}
          onClick={() => void carregar()}
        >
          Atualizar lista
        </button>

        {carregando ? (
          <p role="status">Carregando alunos...</p>
        ) : alunos.length === 0 ? (
          <p>Nenhum aluno cadastrado.</p>
        ) : (
          <div style={{ overflowX: "auto", marginTop: "16px" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
              }}
            >
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Matrícula</th>
                  <th scope="col">Situação</th>
                  <th scope="col">Ações</th>
                </tr>
              </thead>

              <tbody>
                {alunos.map((aluno) => (
                  <tr key={aluno.id}>
                    <td>{aluno.nome_completo}</td>
                    <td>
                      {aluno.matricula_institucional ?? "—"}
                    </td>
                    <td>
                      {aluno.ativo ? "Ativo" : "Inativo"}
                    </td>
                    <td>
                      <button
                        type="button"
                        disabled={salvando}
                        onClick={() => iniciarEdicao(aluno)}
                      >
                        Editar
                      </button>{" "}
                      <button
                        type="button"
                        disabled={salvando}
                        onClick={() =>
                          void alterarSituacao(aluno)
                        }
                      >
                        {aluno.ativo
                          ? "Desativar"
                          : "Reativar"}
                      </button>
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
