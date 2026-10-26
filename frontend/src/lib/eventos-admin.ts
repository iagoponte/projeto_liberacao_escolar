
import { apiRequest } from "./api";

/**
 * Modalidades de aplicação de um evento escolar.
 *
 * INFORMATIVO:
 *   Apenas informa o evento, sem modificar a grade regular.
 *
 * SUBSTITUICAO_PARCIAL:
 *   Substitui as aulas que coincidirem com o intervalo informado.
 *
 * SUBSTITUICAO_INTEGRAL:
 *   Substitui toda a programação regular das datas abrangidas.
 */
export type ModoAplicacaoEvento =
  | "INFORMATIVO"
  | "SUBSTITUICAO_PARCIAL"
  | "SUBSTITUICAO_INTEGRAL";

/**
 * Campos referentes à modalidade e aos horários do evento.
 *
 * Os horários são representados por strings no formato HH:MM
 * ou HH:MM:SS, conforme retornados pelo FastAPI.
 *
 * null indica que o evento não possui horário específico.
 */
export interface CamposHorarioEvento {
  modo_aplicacao: ModoAplicacaoEvento;
  hora_inicio: string | null;
  hora_fim: string | null;
}

/**
 * Representação de um evento escolar retornado pela API.
 */
export interface EventoAdmin extends CamposHorarioEvento {
  id: number;
  turma_id: number;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  ativo: boolean;
}

/**
 * Dados utilizados na criação de um evento.
 *
 * Os campos de horário são opcionais para preservar
 * a compatibilidade com eventos informativos antigos.
 *
 * A validação definitiva ocorre no backend.
 */
export interface DadosEvento {
  turma_id: number;
  titulo: string;
  data_inicio: string;
  data_fim: string;

  modo_aplicacao?: ModoAplicacaoEvento;
  hora_inicio?: string | null;
  hora_fim?: string | null;
}

/**
 * Campos permitidos na atualização parcial de um evento.
 *
 * Somente os atributos enviados serão alterados.
 *
 * hora_inicio e hora_fim podem receber null para
 * remover um intervalo previamente cadastrado.
 */
export type AtualizacaoEvento = Partial<DadosEvento>;

/**
 * Filtros disponíveis para consultar eventos escolares.
 */
export interface FiltrosEventos {
  turma_id?: number;
  data_inicio?: string;
  data_fim?: string;
}

/**
 * Lista os eventos ativos cadastrados pela administração.
 *
 * Permite filtrar por turma e intervalo de datas.
 */
export function listarEventosAdmin(
  filtros: FiltrosEventos = {},
): Promise<EventoAdmin[]> {
  const parametros = new URLSearchParams();

  if (filtros.turma_id !== undefined) {
    parametros.set("turma_id", String(filtros.turma_id));
  }

  if (filtros.data_inicio) {
    parametros.set("data_inicio", filtros.data_inicio);
  }

  if (filtros.data_fim) {
    parametros.set("data_fim", filtros.data_fim);
  }

  const query = parametros.toString();

  return apiRequest<EventoAdmin[]>(
    `/admin/eventos${query ? `?${query}` : ""}`,
  );
}

/**
 * Cria um novo evento escolar.
 *
 * A API verifica:
 * - existência e situação da turma;
 * - validade das datas;
 * - validade dos horários;
 * - requisitos da modalidade;
 * - conflitos entre eventos substitutivos.
 *
 * Requer sessão administrativa e token CSRF.
 */
export function criarEventoAdmin(
  dados: DadosEvento,
  csrfToken: string,
): Promise<EventoAdmin> {
  return apiRequest<EventoAdmin>("/admin/eventos", {
    method: "POST",
    csrfToken,
    body: JSON.stringify(dados),
  });
}

/**
 * Atualiza parcialmente um evento existente.
 *
 * O backend valida os campos enviados juntamente
 * com os valores atuais do evento.
 *
 * A própria atualização não deve ser considerada
 * um conflito com o evento editado.
 */
export function atualizarEventoAdmin(
  eventoId: number,
  dados: AtualizacaoEvento,
  csrfToken: string,
): Promise<EventoAdmin> {
  return apiRequest<EventoAdmin>(
    `/admin/eventos/${eventoId}`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify(dados),
    },
  );
}

/**
 * Desativa logicamente um evento escolar.
 *
 * O registro permanece no PostgreSQL,
 * mas deixa de aparecer nas consultas de eventos ativos.
 */
export function desativarEventoAdmin(
  eventoId: number,
  csrfToken: string,
): Promise<void> {
  return apiRequest<void>(
    `/admin/eventos/${eventoId}`,
    {
      method: "DELETE",
      csrfToken,
    },
  );
}

/**
 * Retorna uma descrição legível da modalidade,
 * útil para tabelas e formulários administrativos.
 */
export function obterDescricaoModoEvento(
  modo: ModoAplicacaoEvento,
): string {
  switch (modo) {
    case "INFORMATIVO":
      return "Informativo";

    case "SUBSTITUICAO_PARCIAL":
      return "Substituição parcial";

    case "SUBSTITUICAO_INTEGRAL":
      return "Substituição integral";
  }
}

/**
 * Formata o intervalo horário para apresentação.
 *
 * Exemplo:
 * "14:50:00", "17:00:00" -> "14:50 às 17:00"
 *
 * Quando não há horários, retorna "Dia inteiro".
 */
export function formatarHorarioEvento(
  horaInicio: string | null,
  horaFim: string | null,
): string {
  if (!horaInicio || !horaFim) {
    return "Dia inteiro";
  }

  return `${horaInicio.slice(0, 5)} às ${horaFim.slice(0, 5)}`;
}
