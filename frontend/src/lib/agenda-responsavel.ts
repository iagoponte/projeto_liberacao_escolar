
import { apiRequest } from "./api";

export interface EventoAgendaResponsavel {
  id: number;
  turma_id: number;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  ativo: boolean;
}

export interface FiltrosAgendaResponsavel {
  data_inicio?: string;
  data_fim?: string;
}

export async function consultarAgendaResponsavel(
  filtros: FiltrosAgendaResponsavel = {},
): Promise<EventoAgendaResponsavel[]> {
  const parametros = new URLSearchParams();

  if (filtros.data_inicio) {
    parametros.set("data_inicio", filtros.data_inicio);
  }

  if (filtros.data_fim) {
    parametros.set("data_fim", filtros.data_fim);
  }

  const query = parametros.toString();

  const endpoint = query
    ? `/responsavel/agenda?${query}`
    : "/responsavel/agenda";

  return apiRequest<EventoAgendaResponsavel[]>(endpoint);
}
