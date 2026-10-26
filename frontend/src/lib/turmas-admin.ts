
import { apiRequest } from "./api";

export interface TurmaAdmin {
  id: number;
  identificacao: string;
  ano_escolar: number;
  ano_letivo_id: number;
  turno: string;
  ativo: boolean;
}

export interface DadosTurma {
  identificacao: string;
  ano_escolar: number;
  ano_letivo_id: number;
  turno: string;
}

export function listarTurmasAdmin(
  anoLetivoId?: number,
): Promise<TurmaAdmin[]> {
  const filtro = anoLetivoId
    ? `?ano_letivo_id=${anoLetivoId}`
    : "";

  return apiRequest<TurmaAdmin[]>(
    `/admin/turmas${filtro}`,
  );
}

export function criarTurmaAdmin(
  dados: DadosTurma,
  csrfToken: string,
): Promise<TurmaAdmin> {
  return apiRequest<TurmaAdmin>("/admin/turmas", {
    method: "POST",
    csrfToken,
    body: JSON.stringify(dados),
  });
}

export function alterarSituacaoTurma(
  id: number,
  ativo: boolean,
  csrfToken: string,
): Promise<TurmaAdmin> {
  return apiRequest<TurmaAdmin>(
    `/admin/turmas/${id}`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify({ ativo }),
    },
  );
}
