
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useAdminSession } from "@/contexts/AdminSessionContext";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  listarAlunosAdmin,
  type AlunoAdmin,
} from "@/lib/alunos-admin";

import {
  listarResponsaveisAdmin,
  type ResponsavelAdmin,
} from "@/lib/responsaveis-admin";

import {
  criarVinculoAdmin,
  listarVinculosAluno,
  reativarVinculoAdmin,
  revogarVinculoAdmin,
  type VinculoAdmin,
} from "@/lib/vinculos-admin";

export default function VinculosAdminPage() {
  const { csrf_token } = useAdminSession();
  const { replace } = useRouter();

  const [alunos, setAlunos] = useState<AlunoAdmin[]>([]);
  const [responsaveis, setResponsaveis] =
    useState<ResponsavelAdmin[]>([]);
  const [vinculos, setVinculos] = useState<VinculoAdmin[]>([]);

  const [alunoId, setAlunoId] = useState("");
  const [responsavelId, setResponsavelId] = useState("");

  const [carregando, setCarregando] = useState(true);
  const [carregandoVinculos, setCarregandoVinculos] =
    useState(false);
  const [salvando, setSalvando] = useState(false);
  const [sessaoExpirada, setSessaoExpirada] =
    useState(false);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);

  // Descarta respostas de consultas anteriores.
  const consultaAtual = useRef(0);
  const sessaoExpiradaRef = useRef(false);

  const tratarErro = useCallback(
    (falha: unknown) => {
      const tipo = classificarErroHttp(falha);

      if (tipo === "NAO_AUTENTICADO") {
        sessaoExpiradaRef.current = true;
        setSessaoExpirada(true);
        setVinculos([]);
        replace("/login");
        return;
      }

      if (tipo === "ACESSO_NEGADO") {
        setErro("Acesso administrativo negado.");
        return;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível concluir a operação.",
      );
    },
    [replace],
  );

  useEffect(() => {
    let ativo = true;

    async function iniciar() {
      try {
        const [listaAlunos, listaResponsaveis] =
          await Promise.all([
            listarAlunosAdmin(),
            listarResponsaveisAdmin(),
          ]);

        if (!ativo || sessaoExpiradaRef.current) return;

        setAlunos(listaAlunos);
        setResponsaveis(listaResponsaveis);
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

  async function consultarVinculos(id: number) {
    const consulta = ++consultaAtual.current;

    setCarregandoVinculos(true);
    setErro(null);

    try {
      const resultado = await listarVinculosAluno(id);

      if (
        consulta !== consultaAtual.current ||
        sessaoExpiradaRef.current
      ) {
        return;
      }

      setVinculos(resultado);
    } catch (falha) {
      if (consulta === consultaAtual.current) {
        setVinculos([]);
        tratarErro(falha);
      }
    } finally {
      if (consulta === consultaAtual.current) {
        setCarregandoVinculos(false);
      }
    }
  }

  function selecionarAluno(valor: string) {
    // Invalida consultas em andamento.
    consultaAtual.current += 1;

    setAlunoId(valor);
    setResponsavelId("");
    setVinculos([]);
    setErro(null);
    setSucesso(null);
    setCarregandoVinculos(false);

    if (valor) {
      void consultarVinculos(Number(valor));
    }
  }

  async function criarVinculo() {
    if (!alunoId || !responsavelId || salvando) return;

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const criado = await criarVinculoAdmin(
        Number(alunoId),
        Number(responsavelId),
        csrf_token,
      );

      setVinculos((atuais) => [criado, ...atuais]);
      setResponsavelId("");
      setSucesso("Vínculo criado com sucesso.");
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  async function alterarVinculo(
    vinculo: VinculoAdmin,
    acao: "REVOGAR" | "REATIVAR",
  ) {
    if (salvando) return;

    const descricao =
      acao === "REVOGAR" ? "revogar" : "reativar";

    if (
      !window.confirm(
        `Deseja ${descricao} este vínculo?`,
      )
    ) {
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const resultado =
        acao === "REVOGAR"
          ? await revogarVinculoAdmin(
              vinculo.id,
              csrf_token,
            )
          : await reativarVinculoAdmin(
              vinculo.id,
              csrf_token,
            );

      if (acao === "REVOGAR") {
        setVinculos((atuais) =>
          atuais.map((item) =>
            item.id === resultado.id ? resultado : item,
          ),
        );
      } else {
        // Reativar cria outro registro, preservando o anterior.
        setVinculos((atuais) => [resultado, ...atuais]);
      }

      setSucesso(
        acao === "REVOGAR"
          ? "Vínculo revogado."
          : "Novo vínculo ativo criado.",
      );
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  const alunoSelecionado = alunos.find(
    (aluno) => aluno.id === Number(alunoId),
  );

  const responsaveisDisponiveis = responsaveis.filter(
    (responsavel) =>
      responsavel.ativo &&
      responsavel.usuario_ativo &&
      !vinculos.some(
        (vinculo) =>
          vinculo.responsavel_id === responsavel.id &&
          vinculo.ativo,
      ),
  );

  function nomeResponsavel(id: number) {
    const responsavel = responsaveis.find(
      (item) => item.id === id,
    );

    return responsavel?.nome_completo ??
      `Responsável #${id}`;
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

      <h1>Vínculos entre responsáveis e alunos</h1>

      <p>
        Gerencie as autorizações de acesso e liberação
        dos alunos.
      </p>

      {erro && <p role="alert">{erro}</p>}
      {sucesso && <p role="status">{sucesso}</p>}

      {carregando ? (
        <p role="status">Carregando cadastros...</p>
      ) : (
        <>
          <section style={{ marginTop: "24px" }}>
            <h2>Selecionar aluno</h2>

            <label htmlFor="aluno-vinculo">Aluno</label>

            <select
              id="aluno-vinculo"
              value={alunoId}
              disabled={salvando}
              onChange={(evento) =>
                selecionarAluno(evento.target.value)
              }
            >
              <option value="">Selecione um aluno</option>

              {alunos.map((aluno) => (
                <option key={aluno.id} value={aluno.id}>
                  {aluno.nome_completo}
                  {!aluno.ativo ? " (inativo)" : ""}
                </option>
              ))}
            </select>
          </section>

          {alunoSelecionado && (
            <>
              <section style={{ marginTop: "32px" }}>
                <h2>Criar vínculo</h2>

                <label htmlFor="responsavel-vinculo">
                  Responsável
                </label>

                <select
                  id="responsavel-vinculo"
                  value={responsavelId}
                  disabled={
                    salvando ||
                    carregandoVinculos ||
                    !alunoSelecionado.ativo
                  }
                  onChange={(evento) =>
                    setResponsavelId(evento.target.value)
                  }
                >
                  <option value="">
                    Selecione um responsável
                  </option>

                  {responsaveisDisponiveis.map(
                    (responsavel) => (
                      <option
                        key={responsavel.id}
                        value={responsavel.id}
                      >
                        {responsavel.nome_completo} —{" "}
                        {responsavel.email}
                      </option>
                    ),
                  )}
                </select>

                <button
                  type="button"
                  disabled={
                    !responsavelId ||
                    salvando ||
                    carregandoVinculos ||
                    !alunoSelecionado.ativo
                  }
                  onClick={() => void criarVinculo()}
                >
                  {salvando
                    ? "Processando..."
                    : "Criar vínculo"}
                </button>
              </section>

              <section style={{ marginTop: "32px" }}>
                <h2>Histórico de vínculos</h2>

                {carregandoVinculos ? (
                  <p role="status">
                    Consultando vínculos...
                  </p>
                ) : vinculos.length === 0 ? (
                  <p>Nenhum vínculo encontrado.</p>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Responsável</th>
                          <th scope="col">Situação</th>
                          <th scope="col">Vigência</th>
                          <th scope="col">Ações</th>
                        </tr>
                      </thead>

                      <tbody>
                        {vinculos.map((vinculo) => (
                          <tr key={vinculo.id}>
                            <td>
                              {nomeResponsavel(
                                vinculo.responsavel_id,
                              )}
                            </td>

                            <td>
                              {vinculo.ativo
                                ? "Ativo"
                                : "Revogado"}
                            </td>

                            <td>
                              {new Date(
                                vinculo.vigente_desde,
                              ).toLocaleString("pt-BR")}
                            </td>

                            <td>
                              <button
                                type="button"
                                disabled={
                                  salvando ||
                                  carregandoVinculos ||
                                  (!vinculo.ativo &&
                                    vinculos.some(
                                        (outro) =>
                                        outro.ativo &&
                                        outro.responsavel_id === vinculo.responsavel_id,
                                    ))
                                }
                                onClick={() =>
                                  void alterarVinculo(
                                    vinculo,
                                    vinculo.ativo
                                      ? "REVOGAR"
                                      : "REATIVAR",
                                  )
                                }
                              >
                                {vinculo.ativo
                                  ? "Revogar"
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
            </>
          )}
        </>
      )}
    </main>
  );
}
