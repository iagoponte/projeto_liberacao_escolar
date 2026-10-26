
import { apiRequest } from "./api";

export interface VinculoAdmin {
  id: number;
  responsavel_id: number;
  aluno_id: number;
  vigente_desde: string;
  revogado_em: string | null;
  ativo: boolean;
}

export function listarVinculosAluno(alunoId: number) {
  return apiRequest<VinculoAdmin[]>(
    `/admin/vinculos?aluno_id=${alunoId}`,
  );
}

export function criarVinculoAdmin(
  alunoId: number,
  responsavelId: number,
  csrfToken: string,
) {
  return apiRequest<VinculoAdmin>("/admin/vinculos", {
    method: "POST",
    csrfToken,
    body: JSON.stringify({
      aluno_id: alunoId,
      responsavel_id: responsavelId,
    }),
  });
}

export function revogarVinculoAdmin(
  vinculoId: number,
  csrfToken: string,
) {
  return apiRequest<VinculoAdmin>(
    `/admin/vinculos/${vinculoId}/revogar`,
    {
      method: "POST",
      csrfToken,
    },
  );
}

export function reativarVinculoAdmin(
  vinculoId: number,
  csrfToken: string,
) {
  return apiRequest<VinculoAdmin>(
    `/admin/vinculos/${vinculoId}/reativar`,
    {
      method: "POST",
      csrfToken,
    },
  );
}
