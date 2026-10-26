
import { apiRequest } from "./api";

export interface AnoLetivo {
  id: number;
  ano: number;
  ativo: boolean;
}

export function listarAnosLetivos(): Promise<AnoLetivo[]> {
  return apiRequest<AnoLetivo[]>("/admin/anos-letivos");
}

export function criarAnoLetivo(
  ano: number,
  csrfToken: string,
): Promise<AnoLetivo> {
  return apiRequest<AnoLetivo>("/admin/anos-letivos", {
    method: "POST",
    csrfToken,
    body: JSON.stringify({ ano }),
  });
}

export function atualizarAnoLetivo(
  id: number,
  ativo: boolean,
  csrfToken: string,
): Promise<AnoLetivo> {
  return apiRequest<AnoLetivo>(
    `/admin/anos-letivos/${id}`,
    {
      method: "PATCH",
      csrfToken,
      body: JSON.stringify({ ativo }),
    },
  );
}
