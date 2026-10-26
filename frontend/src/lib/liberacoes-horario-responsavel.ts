
import { apiRequest } from "./api";

export type EstadoLiberacao =
  | "SEM_REGISTRO"
  | "LIBERADO"
  | "CANCELADO";

export type AcaoLiberacao =
  | "LIBERAR"
  | "CANCELAR";

export interface SituacaoLiberacao {
  aluno_id: number;
  data: string;
  estado: EstadoLiberacao;
  horario_inicio_liberacao: string | null;
}

export interface LiberacaoResposta {
  aluno_id: number;
  data: string;
  estado: "LIBERADO" | "CANCELADO";
  horario_inicio_liberacao: string | null;
}

export interface LiberacaoPedido {
  acao: AcaoLiberacao;
  horario_inicio_liberacao: string | null;
}

/**
 * Consulta a situação atual de todos os alunos
 * vinculados ao responsável autenticado.
 *
 * Pressupõe que /responsavel/liberacoes/hoje
 * retorne uma lista de situações.
 */
export function listarLiberacoesHoje(): Promise<
  SituacaoLiberacao[]
> {
  return apiRequest<SituacaoLiberacao[]>(
    "/responsavel/liberacoes/hoje",
  );
}

/**
 * Executa uma liberação, correção ou cancelamento.
 */
export function alterarLiberacaoHorario(
  alunoId: number,
  dados: LiberacaoPedido,
  csrfToken: string,
): Promise<LiberacaoResposta> {
  return apiRequest<LiberacaoResposta>(
    `/responsavel/alunos/${alunoId}/liberacao`,
    {
      method: "POST",
      csrfToken,
      body: JSON.stringify(dados),
    },
  );
}
