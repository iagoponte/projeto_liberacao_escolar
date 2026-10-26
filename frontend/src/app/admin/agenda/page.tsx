
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { useAdminSession } from "@/contexts/AdminSessionContext";

import {
  classificarErroHttp,
} from "@/lib/erros-http";

import {
  listarAnosLetivos,
  type AnoLetivo,
} from "@/lib/anos-letivos-admin";

import {
  listarTurmasAdmin,
  type TurmaAdmin,
} from "@/lib/turmas-admin";

import {
  consultarAgendaEfetivaAdmin,
  formatarDataAgenda,
  formatarHoraAgenda,
  type AgendaEfetivaAdmin,
  type AtividadeEfetiva,
} from "@/lib/agenda-efetiva-admin";

// ============================================================
// Funções auxiliares
// ============================================================

function dataLocalHoje(): string {
  const agora = new Date();

  const ano = agora.getFullYear();
  const mes = String(
    agora.getMonth() + 1,
  ).padStart(2, "0");
  const dia = String(
    agora.getDate(),
  ).padStart(2, "0");

  return `${ano}-${mes}-${dia}`;
}

function identificarTipo(
  atividade: AtividadeEfetiva,
): string {
  if (atividade.origem === "EVENTO") {
    return "Evento substitutivo";
  }

  if (atividade.tipo === "INTERVALO") {
    return "Intervalo";
  }

  return "Aula regular";
}

function formatarPeriodo(
  inicio: string | null,
  fim: string | null,
): string {
  if (!inicio || !fim) {
    return "Sem horário específico";
  }

  return (
    `${formatarHoraAgenda(inicio)} às ` +
    formatarHoraAgenda(fim)
  );
}

// ============================================================
// Página
// ============================================================

export default function AgendaEfetivaAdminPage() {
  // Mantém a integração com a sessão administrativa.
  useAdminSession();

  const { replace } = useRouter();

  const [anos, setAnos] = useState<AnoLetivo[]>([]);
  const [turmas, setTurmas] = useState<TurmaAdmin[]>([]);

  const [anoSelecionado, setAnoSelecionado] =
    useState("");

  const [turmaSelecionada, setTurmaSelecionada] =
    useState("");

  const [dataSelecionada, setDataSelecionada] =
    useState(dataLocalHoje);

  const [agenda, setAgenda] =
    useState<AgendaEfetivaAdmin | null>(null);

  const [carregandoCadastros, setCarregandoCadastros] =
    useState(true);

  const [consultando, setConsultando] =
    useState(false);

  const [sessaoExpirada, setSessaoExpirada] =
    useState(false);

  const [erro, setErro] =
    useState<string | null>(null);

  // ==========================================================
  // Tratamento de erros
  // ==========================================================

  const tratarErro = useCallback(
    (falha: unknown) => {
      const classificacao = classificarErroHttp(falha);

      if (classificacao === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        setAgenda(null);
        replace("/login");
        return;
      }

      if (classificacao === "ACESSO_NEGADO") {
        setErro(
          "Você não possui autorização para consultar esta agenda.",
        );
        return;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível consultar a agenda.",
      );
    },
    [replace],
  );

  // ==========================================================
  // Carregar anos e turmas
  // ==========================================================

  useEffect(() => {
    let ativo = true;

    async function carregarCadastros() {
      try {
        const [anosObtidos, turmasObtidas] =
          await Promise.all([
            listarAnosLetivos(),
            listarTurmasAdmin(),
          ]);

        if (!ativo) return;

        setAnos(anosObtidos);
        setTurmas(turmasObtidas);
      } catch (falha) {
        if (ativo) {
          tratarErro(falha);
        }
      } finally {
        if (ativo) {
          setCarregandoCadastros(false);
        }
      }
    }

    void carregarCadastros();

    return () => {
      ativo = false;
    };
  }, [tratarErro]);

  // ==========================================================
  // Consultar agenda
  // ==========================================================

  async function consultarAgenda() {
    const turmaId = Number(turmaSelecionada);

    if (
      !Number.isSafeInteger(turmaId) ||
      turmaId <= 0
    ) {
      setErro("Selecione uma turma válida.");
      return;
    }

    if (!dataSelecionada) {
      setErro("Informe a data da consulta.");
      return;
    }

    setConsultando(true);
    setErro(null);
    setAgenda(null);

    try {
      const resultado = await consultarAgendaEfetivaAdmin(
        turmaId,
        dataSelecionada,
      );

      setAgenda(resultado);
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setConsultando(false);
    }
  }

  // ==========================================================
  // Filtros
  // ==========================================================

  const turmasDisponiveis = turmas.filter(
    (turma) =>
      !anoSelecionado ||
      turma.ano_letivo_id ===
        Number(anoSelecionado),
  );

  const turmaAtual = turmas.find(
    (turma) =>
      turma.id === Number(turmaSelecionada),
  );

  const quantidadeAulas =
    agenda?.atividades.filter(
      (atividade) =>
        atividade.tipo === "AULA",
    ).length ?? 0;

  const quantidadeEventos =
    agenda?.atividades.filter(
      (atividade) =>
        atividade.tipo === "EVENTO",
    ).length ?? 0;

  // ==========================================================
  // Renderização
  // ==========================================================

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
      <Link href="/admin">
        Voltar ao painel
      </Link>

      <h1>Agenda escolar efetiva</h1>

      <p>
        Consulte a programação real de cada turma,
        incluindo aulas regulares, provas e demais
        eventos substitutivos.
      </p>

      {/* ========================================= */}
      {/* Seleção da turma e data */}
      {/* ========================================= */}

      <section
        style={{
          marginTop: "24px",
          display: "grid",
          gap: "16px",
          maxWidth: "650px",
        }}
      >
        <h2>Consultar programação</h2>

        {carregandoCadastros ? (
          <p role="status">
            Carregando turmas...
          </p>
        ) : (
          <>
            <div>
              <label htmlFor="ano-agenda">
                Ano letivo
              </label>

              <select
                id="ano-agenda"
                value={anoSelecionado}
                onChange={(event) => {
                  setAnoSelecionado(event.target.value);
                  setTurmaSelecionada("");
                  setAgenda(null);
                  setErro(null);
                }}
              >
                <option value="">
                  Todos os anos
                </option>

                {anos.map((ano) => (
                  <option
                    key={ano.id}
                    value={ano.id}
                  >
                    {ano.ano}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="turma-agenda">
                Turma
              </label>

              <select
                id="turma-agenda"
                value={turmaSelecionada}
                onChange={(event) => {
                  setTurmaSelecionada(event.target.value);
                  setAgenda(null);
                  setErro(null);
                }}
              >
                <option value="">
                  Selecione uma turma
                </option>

                {turmasDisponiveis.map((turma) => (
                  <option
                    key={turma.id}
                    value={turma.id}
                  >
                    {turma.identificacao}
                    {!turma.ativo ? " (inativa)" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="data-agenda">
                Data
              </label>

              <input
                id="data-agenda"
                type="date"
                value={dataSelecionada}
                onChange={(event) => {
                  setDataSelecionada(event.target.value);
                  setAgenda(null);
                  setErro(null);
                }}
              />
            </div>

            <button
              type="button"
              disabled={
                consultando ||
                !turmaSelecionada ||
                !dataSelecionada
              }
              onClick={() => void consultarAgenda()}
            >
              {consultando
                ? "Consultando..."
                : "Consultar agenda"}
            </button>
          </>
        )}
      </section>

      {/* ========================================= */}
      {/* Mensagens */}
      {/* ========================================= */}

      {erro && (
        <p
          role="alert"
          style={{
            color: "crimson",
            marginTop: "20px",
          }}
        >
          {erro}
        </p>
      )}

      {/* ========================================= */}
      {/* Agenda consolidada */}
      {/* ========================================= */}

      {agenda && (
        <section style={{ marginTop: "36px" }}>
          <h2>
            Programação de{" "}
            {formatarDataAgenda(agenda.data)}
          </h2>

          <p>
            <strong>Turma:</strong>{" "}
            {turmaAtual?.identificacao ??
              `Turma #${agenda.turma_id}`}
          </p>

          <p>
            <strong>Aulas:</strong>{" "}
            {quantidadeAulas}
            {" | "}
            <strong>Trechos de eventos:</strong>{" "}
            {quantidadeEventos}
            {" | "}
            <strong>Avisos:</strong>{" "}
            {agenda.informativos.length}
          </p>

          {/* Programação */}

          <div
            style={{
              overflowX: "auto",
              marginTop: "20px",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
              }}
            >
              <thead>
                <tr>
                  <th scope="col">Início</th>
                  <th scope="col">Término</th>
                  <th scope="col">Atividade</th>
                  <th scope="col">Tipo</th>
                </tr>
              </thead>

              <tbody>
                {agenda.atividades.map(
                  (atividade, indice) => (
                    <tr
                      key={
                        `${atividade.hora_inicio}-` +
                        `${atividade.evento_id ?? "grade"}-` +
                        indice
                      }
                    >
                      <td>
                        {formatarHoraAgenda(
                          atividade.hora_inicio,
                        )}
                      </td>

                      <td>
                        {formatarHoraAgenda(
                          atividade.hora_fim,
                        )}
                      </td>

                      <td>
                        <strong>
                          {atividade.descricao}
                        </strong>

                        {atividade.origem ===
                          "EVENTO" && (
                          <span>
                            {" "}
                            (substitui a grade)
                          </span>
                        )}
                      </td>

                      <td>
                        {identificarTipo(atividade)}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>

          {agenda.atividades.length === 0 && (
            <p>
              Nenhuma atividade programada para
              esta data.
            </p>
          )}

          {/* Avisos informativos */}

          <section style={{ marginTop: "32px" }}>
            <h3>Avisos e eventos informativos</h3>

            {agenda.informativos.length === 0 ? (
              <p>
                Nenhum aviso para esta data.
              </p>
            ) : (
              <ul>
                {agenda.informativos.map(
                  (evento) => (
                    <li
                      key={evento.id}
                      style={{
                        marginBottom: "12px",
                      }}
                    >
                      <strong>
                        {evento.titulo}
                      </strong>

                      <span>
                        {" — "}
                        {formatarPeriodo(
                          evento.hora_inicio,
                          evento.hora_fim,
                        )}
                      </span>
                    </li>
                  ),
                )}
              </ul>
            )}
          </section>
        </section>
      )}
    </main>
  );
}
