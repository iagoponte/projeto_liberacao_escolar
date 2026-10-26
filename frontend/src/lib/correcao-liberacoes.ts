import { apiRequest } from "./api";

export type EstadoCorrecao = "LIBERADO" | "CANCELADO";

export interface DadosCorrecaoLiberacao {
  estado: EstadoCorrecao;
  motivo: string;
}

export interface ResultadoCorrecaoLiberacao {
  aluno_id: number;
  data: string;
  estado: EstadoCorrecao;
}

export async function corrigirLiberacaoAdmin(
  alunoId: number,
  dados: DadosCorrecaoLiberacao,
  csrfToken: string,
): Promise<ResultadoCorrecaoLiberacao> {
  // 1. Validar identificador
  if (!Number.isSafeInteger(alunoId) || alunoId <= 0) {
    throw new Error("Identificador do aluno inválido.");
  }

  // 2. Validar justificativa
  const motivo = dados.motivo.trim();

  if (!motivo) {
    throw new Error("A justificativa é obrigatória.");
  }

  // 3. Validar limite previsto no schema do FastAPI
  if (motivo.length > 1000) {
    throw new Error(
      "A justificativa deve ter no máximo 1000 caracteres.",
    );
  }

  // 4. Validar CSRF
  if (!csrfToken.trim()) {
    throw new Error("Token CSRF não informado.");
  }

  // 5. Enviar correção ao backend
  return apiRequest<ResultadoCorrecaoLiberacao>(
    `/admin/alunos/${alunoId}/liberacao`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify({
        estado: dados.estado,
        motivo,
      }),
    },
  );
}

