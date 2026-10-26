
import { apiRequest } from "./api";

export type AcaoLiberacaoResponsavel =
  | "LIBERAR"
  | "CANCELAR";

export type EstadoPersistidoLiberacao =
  | "LIBERADO"
  | "CANCELADO";

export interface ResultadoAcaoLiberacao {
  aluno_id: number;
  data: string;
  estado: EstadoPersistidoLiberacao;
  horario_inicio_liberacao: string | null;
}

export async function alterarLiberacaoResponsavel(
  alunoId: number,
  acao: AcaoLiberacaoResponsavel,
  csrfToken: string,
): Promise<ResultadoAcaoLiberacao> {
  if (!Number.isSafeInteger(alunoId) || alunoId <= 0) {
    throw new Error("Identificador do aluno inválido.");
  }

  if (acao !== "LIBERAR" && acao !== "CANCELAR") {
    throw new Error("Ação de liberação inválida.");
  }

  if (!csrfToken.trim()) {
    throw new Error("Token CSRF não informado.");
  }

  return apiRequest<ResultadoAcaoLiberacao>(
    `/responsavel/alunos/${alunoId}/liberacao`,
    {
      method: "POST",
      csrfToken,
      body: JSON.stringify({ acao }),
    },
  );
}
