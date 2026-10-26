
import { apiRequest } from "./api";

export interface Turma {
  id: number;
  identificacao: string;
  ano_escolar: number;
  ano_letivo_id: number;
  turno: string;
  ativo: boolean;
}

/**
 * Consulta as turmas ativas cadastradas pela escola.
 */
export async function listarTurmasAtivas(): Promise<Turma[]> {
  return apiRequest<Turma[]>(
    "/admin/turmas?ativo=true",
  );
}
