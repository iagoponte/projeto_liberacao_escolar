
import { apiRequest } from "./api";

export type EstadoHistorico =
  | "LIBERADO"
  | "CANCELADO";

export type TipoAcaoHistorico =
  | "LIBERACAO"
  | "CANCELAMENTO"
  | "CORRECAO_ADMIN";

export type PerfilHistorico =
  | "ADMIN"
  | "RESPONSAVEL";

export interface RegistroHistoricoLiberacao {
  id: number;
  liberacao_id: number;
  aluno_id: number;
  usuario_id: number;
  perfil: PerfilHistorico;
  ocorrido_em: string;

  estado_anterior: EstadoHistorico | null;
  novo_estado: EstadoHistorico;

  // Horários associados à alteração auditada.
  horario_anterior: string | null;
  horario_novo: string | null;

  tipo_acao: TipoAcaoHistorico;
  motivo: string | null;
}

export async function consultarHistoricoLiberacoes(
  alunoId: number,
): Promise<RegistroHistoricoLiberacao[]> {
  if (!Number.isSafeInteger(alunoId) || alunoId <= 0) {
    throw new Error("Identificador do aluno inválido.");
  }

  return apiRequest<RegistroHistoricoLiberacao[]>(
    `/admin/alunos/${alunoId}/liberacoes/historico`,
  );
}
