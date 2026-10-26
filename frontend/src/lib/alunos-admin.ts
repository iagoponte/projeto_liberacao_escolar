
import { apiRequest } from "./api";

export interface AlunoAdmin {
  id: number;
  nome_completo: string;
  matricula_institucional: string | null;
  ativo: boolean;
}

export interface DadosAluno {
  nome_completo: string;
  matricula_institucional: string | null;
}

export type AtualizacaoAluno = Partial<
  DadosAluno & { ativo: boolean }
>;

export function listarAlunosAdmin(): Promise<AlunoAdmin[]> {
  return apiRequest<AlunoAdmin[]>("/admin/alunos");
}

export function criarAlunoAdmin(
  dados: DadosAluno,
  csrfToken: string,
): Promise<AlunoAdmin> {
  return apiRequest<AlunoAdmin>("/admin/alunos", {
    method: "POST",
    csrfToken,
    body: JSON.stringify(dados),
  });
}

export function atualizarAlunoAdmin(
  alunoId: number,
  dados: AtualizacaoAluno,
  csrfToken: string,
): Promise<AlunoAdmin> {
  return apiRequest<AlunoAdmin>(
    `/admin/alunos/${alunoId}`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify(dados),
    },
  );
}
