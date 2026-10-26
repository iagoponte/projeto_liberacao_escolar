
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("envia cookies nas requisições", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true }),
        { status: 200 },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const resultado = await apiRequest<{
      ok: boolean;
    }>("/health");

    expect(resultado).toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({
        credentials: "include",
        cache: "no-store",
      }),
    );
  });

  it("envia o token CSRF", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true }),
        { status: 200 },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/exemplo", {
      method: "POST",
      csrfToken: "token-teste",
      body: JSON.stringify({
        acao: "LIBERAR",
      }),
    });

    const [, options] = fetchMock.mock.calls[0];

    const headers = options.headers as Headers;

    expect(
      headers.get("X-CSRF-Token"),
    ).toBe("token-teste");

    expect(
      headers.get("Content-Type"),
    ).toBe("application/json");
  });

  it("trata erros HTTP", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Acesso negado.",
          }),
          { status: 403 },
        ),
      ),
    );

    await expect(
      apiRequest("/admin/liberacoes"),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      message: "Acesso negado.",
    });
  });

  it("aceita respostas sem conteúdo", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, { status: 204 }),
      ),
    );

    const resultado = await apiRequest<void>(
      "/admin/eventos/1",
      { method: "DELETE" },
    );

    expect(resultado).toBeUndefined();
  });
});
