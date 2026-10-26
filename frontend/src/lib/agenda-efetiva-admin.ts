
import { apiRequest } from "./api";

export interface AtividadeEfetiva {
  hora_inicio: string;
  hora_fim: string;
  descricao: string;
  tipo: "AULA" | "INTERVALO" | "EVENTO";
  origem: "GRADE" | "EVENTO";
  evento_id: number | null;
}

export interface EventoInformativo {
  id: number;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  hora_inicio: string | null;
  hora_fim: string | null;
  modo_aplicacao: string;
}

export interface AgendaEfetivaAdmin {
  turma_id: number;
  data: string;
  atividades: AtividadeEfetiva[];
  informativos: EventoInformativo[];
}

/**
 * Consulta a programação real de uma turma.
 *
 * Os eventos substitutivos já são aplicados
 * pelo serviço de consolidação no backend.
 */
export function consultarAgendaEfetivaAdmin(
  turmaId: number,
  data: string,
): Promise<AgendaEfetivaAdmin> {
  if (
    !Number.isSafeInteger(turmaId) ||
    turmaId <= 0
  ) {
    throw new Error("Turma inválida.");
  }

  if (!/^\d{4}-\d{2}-\d{2}$/.test(data)) {
    throw new Error("Data inválida.");
  }

  const parametros = new URLSearchParams({
    data,
  });

  return apiRequest<AgendaEfetivaAdmin>(
    `/admin/turmas/${turmaId}/agenda?${parametros.toString()}`,
  );
}

/**
 * Formata horários ISO enviados pelo FastAPI.
 */
export function formatarHoraAgenda(
  horario: string,
): string {
  return horario.slice(0, 5);
}

/**
 * Formata uma data YYYY-MM-DD para DD/MM/YYYY
 * sem conversão de fuso horário.
 */
export function formatarDataAgenda(
  data: string,
): string {
  const [ano, mes, dia] = data.split("-");

  if (!ano || !mes || !dia) {
    return data;
  }

  return `${dia}/${mes}/${ano}`;
}
