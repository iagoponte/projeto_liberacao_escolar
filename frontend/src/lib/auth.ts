
import { apiRequest } from "./api";

export type Perfil = "ADMIN" | "RESPONSAVEL";

export interface Usuario {
  id: number;
  email: string;
  perfil: Perfil;
}

export interface Sessao {
  usuario: Usuario;
  csrf_token: string;
}

export interface LoginInput {
  email: string;
  senha: string;
}

/**
 * Autentica o usuário no FastAPI.
 *
 * O backend cria o cookie HttpOnly.
 * O frontend recebe os dados da sessão e o CSRF.
 */
export async function fazerLogin(
  credenciais: LoginInput,
): Promise<Sessao> {
  return apiRequest<Sessao>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credenciais),
  });
}

/**
 * Recupera a sessão autenticada.
 *
 * Útil após atualizar a página.
 */
export async function obterSessao(): Promise<Sessao> {
  return apiRequest<Sessao>("/auth/me");
}

/**
 * Encerra a sessão no backend.
 *
 * O cookie será invalidado pelo FastAPI.
 */
export async function fazerLogout(
  csrfToken: string,
): Promise<void> {
  return apiRequest<void>("/auth/logout", {
    method: "POST",
    csrfToken,
  });
}
