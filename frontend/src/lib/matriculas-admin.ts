
import { apiRequest } from "./api";

export interface MatriculaAdmin {
  id: number;
  aluno_id: number;
  turma_id: number;
  ano_letivo_id: number;
  data_inicio: string;
  data_fim: string | null;
}

export interface DadosMatricula {
  aluno_id: number;
  turma_id: number;
  ano_letivo_id: number;
  data_inicio: string;
  data_fim: string | null;
}

export interface FiltrosMatriculas {
  aluno_id?: number;
  turma_id?: number;
  ano_letivo_id?: number;
  aberta?: boolean;
}

export function listarMatriculas(
  filtros: FiltrosMatriculas = {},
): Promise<MatriculaAdmin[]> {
  const parametros = new URLSearchParams();

  if (filtros.aluno_id !== undefined) {
    parametros.set("aluno_id", String(filtros.aluno_id));
  }

  if (filtros.turma_id !== undefined) {
    parametros.set("turma_id", String(filtros.turma_id));
  }

  if (filtros.ano_letivo_id !== undefined) {
    parametros.set(
      "ano_letivo_id",
      String(filtros.ano_letivo_id),
    );
  }

  if (filtros.aberta !== undefined) {
    parametros.set("aberta", String(filtros.aberta));
  }

  const query = parametros.toString();

  return apiRequest<MatriculaAdmin[]>(
    `/admin/matriculas${query ? `?${query}` : ""}`,
  );
}

export function criarMatricula(
  dados: DadosMatricula,
  csrfToken: string,
): Promise<MatriculaAdmin> {
  return apiRequest<MatriculaAdmin>(
    "/admin/matriculas",
    {
      method: "POST",
      csrfToken,
      body: JSON.stringify(dados),
    },
  );
}

export function encerrarMatricula(
  id: number,
  dataFim: string,
  csrfToken: string,
): Promise<MatriculaAdmin> {
  return apiRequest<MatriculaAdmin>(
    `/admin/matriculas/${id}`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify({ data_fim: dataFim }),
    },
  );
}

export interface ResultadoTransferencia {
  matricula_anterior: MatriculaAdmin;
  nova_matricula: MatriculaAdmin;
}

export function transferirMatricula(
  id: number,
  turmaDestinoId: number,
  dataTransferencia: string,
  csrfToken: string,
): Promise<ResultadoTransferencia> {
  return apiRequest<ResultadoTransferencia>(
    `/admin/matriculas/${id}/transferir`,
    {
      method: "POST",
      csrfToken,
      body: JSON.stringify({
        turma_destino_id: turmaDestinoId,
        data_transferencia: dataTransferencia,
      }),
    },
  );
}
