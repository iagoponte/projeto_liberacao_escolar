
import { apiRequest } from "./api";

export type EstadoLiberacaoResponsavel =
  | "LIBERADO"
  | "CANCELADO"
  | "SEM_REGISTRO";

export interface SituacaoLiberacaoResponsavel {
  aluno_id: number;
  data: string;
  estado: EstadoLiberacaoResponsavel;
  horario_inicio_liberacao: string | null;

}

/**
 * Consulta as liberações do dia escolar atual.
 *
 * A API identifica o responsável pela sessão
 * e retorna somente alunos autorizados.
 */
export async function consultarLiberacoesHoje(): Promise<
  SituacaoLiberacaoResponsavel[]
> {
  return apiRequest<SituacaoLiberacaoResponsavel[]>(
    "/responsavel/liberacoes/hoje",
  );
}
