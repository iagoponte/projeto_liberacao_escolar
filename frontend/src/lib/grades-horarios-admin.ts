

import { apiRequest } from "@/lib/api";

export type TurmaHorario = {
  id: number;
  identificacao: string;
  ano_letivo_id: number;
  ativo: boolean;
};

export type GradeHorarioResposta = {
  id: number;
  turma_id: number;
  vigente_desde: string;
  vigente_ate: string | null;
  horarios: string[];
  hora_termino: string | null;
  total_atividades: number;
};

/**
 * Lista as turmas disponíveis para gerenciamento
 * das grades de horários.
 */
export function listarTurmasParaHorarios(): Promise<
  TurmaHorario[]
> {
  return apiRequest<TurmaHorario[]>(
    "/admin/turmas",
  );
}

/**
 * Consulta as versões de grade de uma turma.
 */
export function listarGradesHorario(
  turmaId: number,
): Promise<GradeHorarioResposta[]> {
  if (!Number.isSafeInteger(turmaId) || turmaId <= 0) {
    throw new Error("Identificador da turma inválido.");
  }

  return apiRequest<GradeHorarioResposta[]>(
    `/admin/turmas/${turmaId}/grades`,
  );
}

/**
 * Importa uma grade semanal em formato CSV.
 *
 * A requisição utiliza o cliente HTTP centralizado,
 * passando pelo proxy do Next.js.
 *
 * Não definir Content-Type manualmente:
 * o navegador adiciona o boundary do FormData.
 */
export async function importarGradeHorario(
  turmaId: number,
  arquivo: File,
  vigenteDesde: string,
  horaTermino: string,
  csrfToken: string,
): Promise<GradeHorarioResposta> {
  if (!Number.isSafeInteger(turmaId) || turmaId <= 0) {
    throw new Error("Identificador da turma inválido.");
  }

  if (!arquivo || arquivo.size === 0) {
    throw new Error("Selecione um arquivo CSV válido.");
  }

  if (!vigenteDesde.trim()) {
    throw new Error("Informe a data de início da vigência.");
  }

  if (!horaTermino.trim()) {
    throw new Error("Informe o horário de término da grade.");
  }

  if (!csrfToken) {
    throw new Error(
      "Sessão inválida. Autentique-se novamente.",
    );
  }

  const formulario = new FormData();

  formulario.append("arquivo", arquivo);
  formulario.append("vigente_desde", vigenteDesde);
  formulario.append("hora_termino", horaTermino);

  return apiRequest<GradeHorarioResposta>(
    `/admin/turmas/${turmaId}/grade/importar`,
    {
      method: "POST",
      body: formulario,
      csrfToken,
    },
  );
}
