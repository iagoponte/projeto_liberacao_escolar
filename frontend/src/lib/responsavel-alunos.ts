import { apiRequest } from "./api";

export interface AlunoResponsavel {
  id: number;
  nome_completo: string;
  matricula_institucional: string | null;
}

/**
 * Retorna os alunos com vínculo vigente
 * com o responsável autenticado.
 *
 * A autorização é realizada pelo FastAPI.
 */
export async function listarAlunosResponsavel(): Promise<
  AlunoResponsavel[]
> {
  return apiRequest<AlunoResponsavel[]>(
    "/responsavel/alunos",
  );
}