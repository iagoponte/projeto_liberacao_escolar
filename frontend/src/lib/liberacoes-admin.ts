
import { apiRequest } from "./api";

export type EstadoLiberacao =
  | "LIBERADO"
  | "CANCELADO"
  | "SEM_REGISTRO";

export interface SituacaoLiberacaoAluno {
  aluno_id: number;
  nome_completo: string;
  matricula_institucional: string;
  turma_id: number;
  data: string;
  estado: EstadoLiberacao;
  horario_inicio_liberacao: string | null;
}

export interface FiltrosLiberacoesAdmin {
  turmaId: number;
  data: string;
  estado?: EstadoLiberacao;
  busca?: string;
}

/**
 * Consulta o estado das liberações de uma turma.
 *
 * A autorização é validada pelo FastAPI
 * utilizando o cookie de sessão.
 */
export async function consultarLiberacoesAdmin(
  filtros: FiltrosLiberacoesAdmin,
): Promise<SituacaoLiberacaoAluno[]> {
  const parametros = new URLSearchParams({
    turma_id: String(filtros.turmaId),
    data: filtros.data,
  });

  if (filtros.estado) {
    parametros.set("estado", filtros.estado);
  }

  if (filtros.busca?.trim()) {
    parametros.set("busca", filtros.busca.trim());
  }

  return apiRequest<SituacaoLiberacaoAluno[]>(
    `/admin/liberacoes?${parametros.toString()}`,
  );
}
