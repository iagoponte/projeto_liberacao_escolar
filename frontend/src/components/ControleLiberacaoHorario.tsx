
"use client";

import { useCallback, useEffect, useState } from "react";

import { useResponsavelSession } from "@/contexts/ResponsavelSessionContext";

import type {
  AgendaEfetivaAluno,
} from "@/lib/agenda-efetiva-responsavel";

import {
  alterarLiberacaoHorario,
  listarLiberacoesHoje,
  type SituacaoLiberacao,
} from "@/lib/liberacoes-horario-responsavel";

interface Props {
  alunoId: number;
  agenda: AgendaEfetivaAluno;
}

function obterDataEscolarAtual(): string {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Fortaleza",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const valores = Object.fromEntries(
    partes.map((parte) => [
      parte.type,
      parte.value,
    ]),
  );

  return (
    `${valores.year}-${valores.month}-${valores.day}`
  );
}

function formatarHora(valor: string): string {
  return valor.slice(0, 5);
}

export function ControleLiberacaoHorario({
  alunoId,
  agenda,
}: Props) {
  const sessao = useResponsavelSession();
  const [situacao, setSituacao] =
    useState<SituacaoLiberacao | null>(null);

  const [horarioSelecionado, setHorarioSelecionado] =
    useState("");

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(
    null,
  );

  const dataAtual = obterDataEscolarAtual();
  const ehHoje = agenda.data === dataAtual;

  // Somente o início de aulas e eventos efetivos
  // pode ser escolhido como horário de liberação.
  const opcoes = agenda.atividades
    .filter(
      (atividade) =>
        atividade.tipo === "AULA" ||
        atividade.tipo === "EVENTO",
    )
    .filter(
      (atividade, indice, atividades) =>
        atividades.findIndex(
          (outra) =>
            outra.hora_inicio ===
            atividade.hora_inicio,
        ) === indice,
    )
    .sort((a, b) =>
      a.hora_inicio.localeCompare(b.hora_inicio),
    );

  // ==========================================================
  // Consultar situação atual
  // ==========================================================

  const carregarSituacao = useCallback(async () => {
    if (!ehHoje) {
      setSituacao(null);
      setHorarioSelecionado("");
      setCarregando(false);
      return;
    }

    setCarregando(true);
    setErro(null);

    try {
      const situacoes = await listarLiberacoesHoje();

      const encontrada = situacoes.find(
        (item) =>
          item.aluno_id === alunoId &&
          item.data === agenda.data,
      );

      const atual = encontrada ?? {
        aluno_id: alunoId,
        data: agenda.data,
        estado: "SEM_REGISTRO" as const,
        horario_inicio_liberacao: null,
      };

      setSituacao(atual);

      setHorarioSelecionado(
        atual.horario_inicio_liberacao?.slice(0, 5) ??
          "",
      );
    } catch (falha) {
      setSituacao(null);

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível consultar a liberação.",
      );
    } finally {
      setCarregando(false);
    }
  }, [alunoId, agenda.data, ehHoje]);

  useEffect(() => {
    void carregarSituacao();
  }, [carregarSituacao]);

  // ==========================================================
  // Liberar ou corrigir horário
  // ==========================================================

  async function confirmarLiberacao() {
    if (salvando || !ehHoje) return;

    if (!horarioSelecionado) {
      setErro(
        "Selecione um horário para a liberação.",
      );
      return;
    }

    if (!sessao.csrf_token) {
      setErro(
        "Sessão indisponível. Faça login novamente.",
      );
      return;
    }

    const confirmado = window.confirm(
      `Confirma a liberação do aluno a partir das ` +
        `${horarioSelecionado}?`,
    );

    if (!confirmado) return;

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const resposta = await alterarLiberacaoHorario(
        alunoId,
        {
          acao: "LIBERAR",
          horario_inicio_liberacao:
            horarioSelecionado,
        },
        sessao.csrf_token,
      );

      setSituacao({
        aluno_id: resposta.aluno_id,
        data: resposta.data,
        estado: resposta.estado,
        horario_inicio_liberacao:
          resposta.horario_inicio_liberacao,
      });

      setHorarioSelecionado(
        resposta.horario_inicio_liberacao?.slice(
          0,
          5,
        ) ?? "",
      );

      setSucesso(
        "Liberação registrada com sucesso.",
      );
    } catch (falha) {
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível registrar a liberação.",
      );
    } finally {
      setSalvando(false);
    }
  }

  // ==========================================================
  // Cancelar liberação
  // ==========================================================

  async function cancelarLiberacao() {
    if (
      salvando ||
      !ehHoje ||
      situacao?.estado !== "LIBERADO"
    ) {
      return;
    }

    if (!sessao.csrf_token) {
      setErro("Sessão indisponível.");
      return;
    }

    if (
      !window.confirm(
        "Confirma o cancelamento da liberação?",
      )
    ) {
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      const resposta = await alterarLiberacaoHorario(
        alunoId,
        {
          acao: "CANCELAR",
          horario_inicio_liberacao: null,
        },
        sessao.csrf_token,
      );

      setSituacao({
        aluno_id: resposta.aluno_id,
        data: resposta.data,
        estado: resposta.estado,
        horario_inicio_liberacao:
          resposta.horario_inicio_liberacao,
      });

      setHorarioSelecionado("");

      setSucesso(
        "Liberação cancelada com sucesso.",
      );
    } catch (falha) {
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível cancelar a liberação.",
      );
    } finally {
      setSalvando(false);
    }
  }

  // ==========================================================
  // Renderização
  // ==========================================================

  return (
    <section
      style={{
        marginTop: "24px",
        padding: "16px",
        border: "1px solid #999",
        borderRadius: "8px",
      }}
    >
      <h4>Autorização de saída</h4>

      {!ehHoje ? (
        <p>
          A liberação só pode ser registrada para
          a data atual da escola. Você pode consultar
          a programação de outras datas, mas não
          pode autorizá-las antecipadamente.
        </p>
      ) : carregando ? (
        <p role="status">
          Consultando liberação atual...
        </p>
      ) : (
        <>
          {situacao && (
            <p>
              <strong>Situação atual: </strong>

              {situacao.estado === "LIBERADO"
                ? `Liberado a partir das ${
                    situacao.horario_inicio_liberacao
                      ? formatarHora(
                          situacao.horario_inicio_liberacao,
                        )
                      : "horário não definido"
                  }`
                : situacao.estado === "CANCELADO"
                  ? "Liberação cancelada"
                  : "Nenhuma liberação registrada"}
            </p>
          )}

          {opcoes.length === 0 ? (
            <p>
              Não há horários disponíveis para
              liberação nesta data.
            </p>
          ) : (
            <>
              <label
                htmlFor={`horario-liberacao-${alunoId}`}
              >
                Liberar a partir da atividade
              </label>

              <select
                id={`horario-liberacao-${alunoId}`}
                value={horarioSelecionado}
                disabled={
                  salvando || situacao === null
                }
                onChange={(event) =>
                  setHorarioSelecionado(
                    event.target.value,
                  )
                }
              >
                <option value="">
                  Selecione o horário
                </option>

                {opcoes.map((atividade) => (
                  <option
                    key={atividade.hora_inicio}
                    value={formatarHora(
                      atividade.hora_inicio,
                    )}
                  >
                    {formatarHora(
                      atividade.hora_inicio,
                    )}
                    {" — "}
                    {atividade.descricao}
                  </option>
                ))}
              </select>

              <p>
                A autorização será válida a partir
                do horário selecionado, incluindo
                as atividades posteriores.
              </p>

              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <button
                  type="button"
                  disabled={
                    salvando ||
                    situacao === null ||
                    !horarioSelecionado ||
                    (
                      situacao.estado === "LIBERADO" &&
                      situacao.horario_inicio_liberacao?.slice(
                        0,
                        5,
                      ) === horarioSelecionado
                    )
                  }
                  onClick={() =>
                    void confirmarLiberacao()
                  }
                >
                  {salvando
                    ? "Salvando..."
                    : situacao?.estado === "LIBERADO"
                      ? "Corrigir horário"
                      : "Confirmar liberação"}
                </button>

                {situacao?.estado === "LIBERADO" && (
                  <button
                    type="button"
                    disabled={salvando}
                    onClick={() =>
                      void cancelarLiberacao()
                    }
                  >
                    Cancelar liberação
                  </button>
                )}
              </div>
            </>
          )}
        </>
      )}

      {erro && (
        <p role="alert" style={{ color: "crimson" }}>
          {erro}
        </p>
      )}

      {sucesso && (
        <p role="status" style={{ color: "green" }}>
          {sucesso}
        </p>
      )}
    </section>
  );
}
