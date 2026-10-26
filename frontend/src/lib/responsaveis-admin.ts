
import { apiRequest } from "./api";

export interface ResponsavelAdmin {
  id: number;
  usuario_id: number;
  nome_completo: string;
  email: string;
  ativo: boolean;
  usuario_ativo: boolean;
}

export interface DadosCriacaoResponsavel {
  nome_completo: string;
  email: string;
  senha: string;
}

export function listarResponsaveisAdmin() {
  return apiRequest<ResponsavelAdmin[]>(
    "/admin/responsaveis",
  );
}

export function criarResponsavelAdmin(
  dados: DadosCriacaoResponsavel,
  csrfToken: string,
) {
  return apiRequest<ResponsavelAdmin>(
    "/admin/responsaveis",
    {
      method: "POST",
      csrfToken,
      body: JSON.stringify(dados),
    },
  );
}
