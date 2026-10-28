
/**
 * Cliente HTTP centralizado do Sistema de Liberação Escolar.
 *
 * Fluxo:
 * Navegador -> Next.js -> Render (FastAPI) -> Neon (PostgreSQL)
 *
 * Todas as requisições utilizam o proxy configurado
 * em frontend/next.config.ts.
 */

const API_URL = "/api/backend";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiOptions = RequestInit & {
  csrfToken?: string;
};

export async function apiRequest<T>(
  endpoint: string,
  options: ApiOptions = {},
): Promise<T> {
  const { csrfToken, headers, ...rest } = options;

  // Evita duplicação de barras e do prefixo do proxy.
  const caminho = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;

  const url = caminho.startsWith(`${API_URL}/`)
    ? caminho
    : `${API_URL}${caminho}`;

  // Preserva cabeçalhos recebidos do chamador.
  const requestHeaders = new Headers(headers);

  // Define JSON somente quando existe corpo e
  // nenhum Content-Type foi informado.
  if (
    rest.body !== undefined &&
    rest.body !== null &&
    !requestHeaders.has("Content-Type") &&
    typeof rest.body === "string"
  ) {
    requestHeaders.set(
      "Content-Type",
      "application/json",
    );
  }

  // Proteção CSRF utilizada pelas operações autenticadas.
  if (csrfToken) {
    requestHeaders.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(url, {
    ...rest,
    headers: requestHeaders,

    // Envia automaticamente o cookie HttpOnly de sessão.
    credentials: "include",

    // Evita utilizar respostas antigas de autenticação.
    cache: "no-store",
  });

  // Tratamento centralizado de erros HTTP.
  if (!response.ok) {
    let message = `Erro HTTP ${response.status}`;

    try {
      const body: unknown = await response.json();

      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof body.detail === "string"
      ) {
        message = body.detail;
      }
    } catch {
      // Mantém a mensagem HTTP padrão.
    }

    throw new ApiError(response.status, message);
  }

  // Requisições sem conteúdo (ex.: HTTP 204).
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

