import { apiRequest } from "./api";

import type {
  AtividadeEfetiva,
  EventoInformativo,
} from "./agenda-efetiva-admin";

export interface AgendaEfetivaAluno {
  aluno_id: number;
  turma_id: number;
  data: string;
  atividades: AtividadeEfetiva[];
  informativos: EventoInformativo[];
}

export function consultarAgendaEfetivaAluno(
  alunoId: number,
  data: string,
): Promise<AgendaEfetivaAluno> {
  const parametros = new URLSearchParams({ data });

  return apiRequest<AgendaEfetivaAluno>(
    `/responsavel/agenda/alunos/${alunoId}/agenda-efetiva?${parametros}`,
  );
}