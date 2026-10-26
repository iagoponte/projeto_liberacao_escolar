
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

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

  const requestHeaders = new Headers(headers);

  if (
    rest.body !== undefined &&
    !requestHeaders.has("Content-Type")
  ) {
    requestHeaders.set(
      "Content-Type",
      "application/json",
    );
  }

  if (csrfToken) {
    requestHeaders.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      ...rest,
      headers: requestHeaders,
      credentials: "include",
      cache: "no-store",
    },
  );

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

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
