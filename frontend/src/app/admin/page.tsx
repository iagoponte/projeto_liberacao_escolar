"use client";

import { FormEvent, useEffect, useCallback, useState, useRef } from "react";
import {
  consultarLiberacoesAdmin,
  type EstadoLiberacao,
  type SituacaoLiberacaoAluno,
  type FiltrosLiberacoesAdmin,
} from "@/lib/liberacoes-admin";

import {
  listarTurmasAtivas,
  type Turma,
} from "@/lib/turmas";

import { calcularIndicadoresLiberacoes } from "@/lib/indicadores-liberacoes";
import HistoricoLiberacoes from "@/components/HistoricoLiberacoes";
import CorrecaoLiberacao from "@/components/CorrecaoLiberacao";
import { useAdminSession } from "@/contexts/AdminSessionContext";
import type {
  ResultadoCorrecaoLiberacao,
} from "@/lib/correcao-liberacoes";

import { useRouter } from "next/navigation";
import { classificarErroHttp } from "@/lib/erros-http";
import Link from "next/link";

export default function AdminPage() {
  const [turmaId, setTurmaId] = useState("");
  const [data, setData] = useState(
    new Date().toLocaleDateString("en-CA"),
  );

  const [alunos, setAlunos] = useState<
    SituacaoLiberacaoAluno[]
  >([]);

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [consultado, setConsultado] = useState(false);
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [carregandoTurmas, setCarregandoTurmas] = useState(true);
  const [erroTurmas, setErroTurmas] = useState<string | null>(null);

  const indicadores = calcularIndicadoresLiberacoes(alunos);
  const [estadoFiltro, setEstadoFiltro] = useState<EstadoLiberacao | "">("");
  const [busca, setBusca] = useState("");
  const [alunosFiltrados, setAlunosFiltrados] = useState<SituacaoLiberacaoAluno[]>([]);
  const requisicaoAtual = useRef(0);
  const ultimaConsulta = useRef<FiltrosLiberacoesAdmin | null>(null,);

  const [alunoHistorico, setAlunoHistorico] = useState<{id: number;nome: string;} | null>(null);
  const sessao = useAdminSession();
  const [alunoCorrecao, setAlunoCorrecao] = useState<SituacaoLiberacaoAluno | null>(null);
  const [atualizandoAposCorrecao, setAtualizandoAposCorrecao] = useState(false);
  const [erroAtualizacao, setErroAtualizacao] = useState<string | null>(null);
  const [mensagemSucesso, setMensagemSucesso] = useState<string | null>(null);
  const { replace } = useRouter();
  const [sessaoExpirada, setSessaoExpirada] = useState(false);
  
 
  const encaminharParaLogin = useCallback(() => {
    setSessaoExpirada(true);
    replace("/login");
  }, [replace]);

  const tratarErroDeAcesso = useCallback(
    (falha: unknown): boolean => {
      if (classificarErroHttp(falha) === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        replace("/login");
        return true;
      }

      return false;
    },
    [encaminharParaLogin],
  );

  useEffect(() => {
    let ativo = true;

    async function carregarTurmas() {
      try {
        const resultado = await listarTurmasAtivas();

        if (!ativo) return;

        setTurmas(resultado);
      
      } catch (falha) {
        if (!ativo) return;

        if (tratarErroDeAcesso(falha)) {
          return;
        }

        if (classificarErroHttp(falha) === "ACESSO_NEGADO") {
          setErroTurmas(
            "Você não possui permissão para consultar as turmas.",
          );
          return;
        }

        setErroTurmas(
          falha instanceof Error
            ? falha.message
            : "Não foi possível carregar as turmas.",
        );
      } finally {
        if (ativo) {
          setCarregandoTurmas(false);
        }
      }
    }

    void carregarTurmas();

    return () => {
      ativo = false;
    };
  }, [tratarErroDeAcesso]);


  
  // async function consultar(evento: FormEvent<HTMLFormElement>) {
  //   evento.preventDefault();

  //   if (!turmaId || !data) return;

  //   const identificador = ++requisicaoAtual.current;

  //   setCarregando(true);
  //   setErro(null);
  //   setConsultado(false);
  //   setAlunos([]);
  //   setAlunosFiltrados([]);
  //   setAlunoHistorico(null);

  //   const filtrosBase = {
  //     turmaId: Number(turmaId),
  //     data,
  //   };

  //   const filtrosAtivos = {
  //     ...filtrosBase,
  //     ...(estadoFiltro ? { estado: estadoFiltro } : {}),
  //     ...(busca.trim() ? { busca: busca.trim() } : {}),
  //   };

  //   const possuiFiltros = Boolean(estadoFiltro || busca.trim());

  //   try {
  //     const consultaGeral = consultarLiberacoesAdmin(filtrosBase);

  //     // Sem filtros, aproveitamos a mesma resposta.
  //     // Com filtros, consultamos separadamente os dados
  //     // gerais e os registros exibidos na tabela.
  //     const consultaFiltrada = possuiFiltros
  //       ? consultarLiberacoesAdmin(filtrosAtivos)
  //       : consultaGeral;

  //     const [resultadoGeral, resultadoFiltrado] =
  //       await Promise.all([
  //         consultaGeral,
  //         consultaFiltrada,
  //       ]);

  //     // Impede que respostas antigas alterem a interface.
  //     if (identificador !== requisicaoAtual.current) {
  //       return;
  //     }

  //     setAlunos(resultadoGeral);
  //     setAlunosFiltrados(resultadoFiltrado);
  //     setConsultado(true);
  //   } catch (falha) {
  //     if (identificador !== requisicaoAtual.current) {
  //       return;
  //     }

  //     setErro(
  //       falha instanceof Error
  //         ? falha.message
  //         : "Não foi possível consultar as liberações.",
  //     );
  //   } finally {
  //     if (identificador === requisicaoAtual.current) {
  //       setCarregando(false);
  //     }
  //   }
  // }

  async function executarConsulta(
    filtros: FiltrosLiberacoesAdmin,
  ): Promise<boolean> {
    const identificador = ++requisicaoAtual.current;

    setCarregando(true);
    setErro(null);
    setConsultado(false);
    setAlunos([]);
    setAlunosFiltrados([]);

    const filtrosBase = {
      turmaId: filtros.turmaId,
      data: filtros.data,
    };

    const possuiFiltros = Boolean(
      filtros.estado || filtros.busca?.trim(),
    );

    try {
      const consultaGeral =
        consultarLiberacoesAdmin(filtrosBase);

      const consultaFiltrada = possuiFiltros
        ? consultarLiberacoesAdmin(filtros)
        : consultaGeral;

      const [resultadoGeral, resultadoFiltrado] =
        await Promise.all([
          consultaGeral,
          consultaFiltrada,
        ]);

      if (identificador !== requisicaoAtual.current) {
        return false;
      }

      setAlunos(resultadoGeral);
      setAlunosFiltrados(resultadoFiltrado);
      setConsultado(true);

      return true;

    } catch (falha) {
      // Uma resposta antiga não deve modificar o painel,
      // mesmo quando representa um erro HTTP.
      if (identificador !== requisicaoAtual.current) {
        return false;
      }

      if (tratarErroDeAcesso(falha)) {
        return false;
      }

      if (classificarErroHttp(falha) === "ACESSO_NEGADO") {
        setErro(
          "Você não possui permissão para consultar estas liberações.",
        );
        return false;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível consultar as liberações.",
      );

      return false;
    } finally {
      if (identificador === requisicaoAtual.current) {
        setCarregando(false);
      }
    }
  }

  async function consultar(
    evento: FormEvent<HTMLFormElement>,
  ) {
    evento.preventDefault();

    if (!turmaId || !data || !Number.isSafeInteger(Number(turmaId))) {
      return;
    }

    setAlunoHistorico(null);
    setAlunoCorrecao(null);
    setErroAtualizacao(null);
    setMensagemSucesso(null);

    const filtros: FiltrosLiberacoesAdmin = {
      turmaId: Number(turmaId),
      data,
      ...(estadoFiltro ? { estado: estadoFiltro } : {}),
      ...(busca.trim() ? { busca: busca.trim() } : {}),
    };

    ultimaConsulta.current = filtros;

    await executarConsulta(filtros);
  }

  
  async function aoCorrigirLiberacao(
    resultado: ResultadoCorrecaoLiberacao,
  ) {
    setAlunoCorrecao(null);
    setAtualizandoAposCorrecao(true);
    setErroAtualizacao(null);
    setMensagemSucesso(null);

    try {
      const filtros = ultimaConsulta.current;

      if (!filtros) {
        setErroAtualizacao(
          "Correção registrada, mas não há consulta para atualizar.",
        );
        return;
      }

      const atualizado = await executarConsulta(filtros);

      if (atualizado) {
        setMensagemSucesso(
          `Correção do aluno #${resultado.aluno_id} registrada com sucesso.`,
        );
      } else {
        setErroAtualizacao(
          "A correção foi registrada, mas não foi possível atualizar os resultados. Consulte novamente.",
        );
      }
    } finally {
      setAtualizandoAposCorrecao(false);
    }
  }

  if (sessaoExpirada) {
    return (
      <main role="status" aria-live="polite">
        Sessão expirada. Redirecionando para o login...
      </main>
    );
  }

  return (
    <main style={{ padding: "32px", maxWidth: "1100px", margin: "0 auto" }}>
      <h1>Liberações escolares</h1>
      <p>Consulte a situação dos alunos por turma e data.</p>
      <p style={{ marginTop: "16px" }}>
        <Link href="/admin/alunos">
          Gerenciar alunos
        </Link>
      </p>
      <p>
        <Link href="/admin/responsaveis">
          Gerenciar responsáveis
        </Link>
      </p>
      <p>
        <Link href="/admin/vinculos">
          Gerenciar vínculos
        </Link>
      </p>
      <p>
        <Link href="/admin/organizacao">
          Gerenciar organização escolar
        </Link>
      </p>
      <p>
        <Link href="/admin/organizacao/horarios">
          Gerenciar horários
        </Link>
      </p>
      <p>
        <Link href="/admin/eventos">
          Gerenciar eventos escolares
        </Link>
      </p>
      <p>
        <Link href="/admin/agenda">
          Consultar agenda efetiva
        </Link>
      </p>
      <form
        onSubmit={consultar}
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          marginTop: "24px",
          marginBottom: "24px",
        }}
      >
        <div>
          <label htmlFor="turma-id">Turma</label>

          <select
            id="turma-id"
            required
            value={turmaId}
            disabled={carregandoTurmas || turmas.length === 0}
            onChange={(evento) => setTurmaId(evento.target.value)}
          >
          <option value="">
            {carregandoTurmas
              ? "Carregando turmas..."
              : "Selecione uma turma"}
          </option>

          {turmas.map((turma) => (
            <option key={turma.id} value={turma.id}>
              {turma.identificacao} — {turma.turno}
            </option>
          ))}
          </select>

          {erroTurmas && (
            <p role="alert">{erroTurmas}</p>
          )}
        </div>

        <div>
          <label htmlFor="data">Data</label>
          <input
            id="data"
            type="date"
            required
            value={data}
            onChange={(evento) => setData(evento.target.value)}
          />
        </div>

        
        <div>
          <label htmlFor="estado-filtro">Estado</label>

          <select
            id="estado-filtro"
            value={estadoFiltro}
            onChange={(evento) =>
              setEstadoFiltro(
                evento.target.value as EstadoLiberacao | "",
              )
            }
          >
            <option value="">Todos os estados</option>
            <option value="LIBERADO">Liberado</option>
            <option value="CANCELADO">Cancelado</option>
            <option value="SEM_REGISTRO">Sem registro</option>
          </select>
        </div>

        <div>
          <label htmlFor="busca-aluno">Pesquisar aluno</label>

          <input
            id="busca-aluno"
            type="search"
            placeholder="Nome ou matrícula"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
          />
        </div>

        <button type="submit" disabled={carregando}>
          {carregando ? "Consultando..." : "Consultar"}
        </button>
      </form>

      {erro && <p role="alert">{erro}</p>}

      
      {consultado && (
        <section
          aria-label="Resultado das liberações"
          style={{ marginTop: "32px" }}
        >
          <h2>Resultados</h2>
          <p>
            Exibindo {alunosFiltrados.length} de {indicadores.total} alunos
          </p>
          {atualizandoAposCorrecao && (
            <p role="status">
              Correção registrada. Atualizando os resultados...
            </p>
          )}

          {mensagemSucesso && (
            <p role="status">{mensagemSucesso}</p>
          )}

          {erroAtualizacao && (
            <p role="alert">{erroAtualizacao}</p>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: "16px",
              marginTop: "20px",
              marginBottom: "28px",
            }}
          >
            {[
              { titulo: "Total de alunos", valor: indicadores.total },
              { titulo: "Liberados", valor: indicadores.liberados },
              { titulo: "Cancelados", valor: indicadores.cancelados },
              { titulo: "Sem registro", valor: indicadores.semRegistro },
            ].map((indicador) => (
              <div
                key={indicador.titulo}
                style={{
                  padding: "20px",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  backgroundColor: "#ffffff",
                }}
              >
                <p style={{ color: "#475569", marginBottom: "8px" }}>
                  {indicador.titulo}
                </p>

                <strong style={{ fontSize: "28px", color: "#17233b" }}>
                  {indicador.valor}
                </strong>
              </div>
            ))}
          </div>

          {alunosFiltrados.length === 0 ? (
            <p>Nenhum aluno encontrado para os critérios selecionados.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  textAlign: "left",
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "2px solid #cbd5e1" }}>
                    <th scope="col" style={{ padding: "12px" }}>
                      Aluno
                    </th>

                    <th scope="col" style={{ padding: "12px" }}>
                      Matrícula
                    </th>

                    <th scope="col" style={{ padding: "12px" }}>
                      Estado
                    </th>
                    <th scope="col">
                      Horário autorizado
                    </th>
                    <th scope="col" style={{ padding: "12px" }}>
                      Ações
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {alunosFiltrados.map((aluno) => {
                    const apresentacao = {
                      LIBERADO: {
                        texto: "Liberado",
                        cor: "#166534",
                        fundo: "#dcfce7",
                      },
                      CANCELADO: {
                        texto: "Cancelado",
                        cor: "#92400e",
                        fundo: "#fef3c7",
                      },
                      SEM_REGISTRO: {
                        texto: "Sem registro",
                        cor: "#475569",
                        fundo: "#f1f5f9",
                      },
                    }[aluno.estado];

                    return (
                      <tr
                        key={aluno.aluno_id}
                        style={{ borderBottom: "1px solid #e2e8f0" }}
                      >
                        <td style={{ padding: "12px" }}>
                          {aluno.nome_completo}
                        </td>

                        <td style={{ padding: "12px" }}>
                          {aluno.matricula_institucional}
                        </td>

                        <td style={{ padding: "12px" }}>
                          <span
                            style={{
                              display: "inline-block",
                              padding: "5px 10px",
                              borderRadius: "999px",
                              fontWeight: 600,
                              fontSize: "13px",
                              color: apresentacao.cor,
                              backgroundColor: apresentacao.fundo,
                            }}
                          >
                            {apresentacao.texto}
                          </span>
                        </td>
                        <td style={{ padding: "12px" }}>
                          {aluno.estado === "LIBERADO"
                            ? aluno.horario_inicio_liberacao?.slice(0, 5) ??
                              "Não definido"
                            : "—"}
                        </td>
                        <td style={{ padding: "12px" }}>
                          <button
                            type="button"
                            onClick={() =>
                              setAlunoHistorico({
                                id: aluno.aluno_id,
                                nome: aluno.nome_completo,
                              })
                            }
                          >
                            Ver histórico
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setAlunoHistorico(null);
                              setAlunoCorrecao(aluno);
                              setMensagemSucesso(null);
                              setErroAtualizacao(null);
                            }}
                          >
                            Corrigir liberação
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {alunoHistorico && (
                <HistoricoLiberacoes
                  key={alunoHistorico.id}
                  alunoId={alunoHistorico.id}
                  nomeAluno={alunoHistorico.nome}
                  onClose={() => setAlunoHistorico(null)}
                  onSessaoExpirada={encaminharParaLogin}
                />
              )}
              {alunoCorrecao && (
                <CorrecaoLiberacao
                  key={alunoCorrecao.aluno_id}
                  alunoId={alunoCorrecao.aluno_id}
                  nomeAluno={alunoCorrecao.nome_completo}
                  estadoAtual={alunoCorrecao.estado}
                  csrfToken={sessao.csrf_token}
                  onClose={() => setAlunoCorrecao(null)}
                  onSuccess={aoCorrigirLiberacao}
                  onSessaoExpirada={encaminharParaLogin}
                />
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
