
import { describe, expect, it } from "vitest";

import { classificarErroHttp } from "./erros-http";

describe("classificarErroHttp", () => {
  it("identifica sessão não autenticada", () => {
    expect(
      classificarErroHttp({ status: 401 }),
    ).toBe("NAO_AUTENTICADO");
  });

  it("distingue acesso proibido de sessão expirada", () => {
    expect(
      classificarErroHttp({ status: 403 }),
    ).toBe("ACESSO_NEGADO");
  });

  it("identifica erros de validação", () => {
    expect(
      classificarErroHttp({ status: 422 }),
    ).toBe("VALIDACAO");
  });

  it("identifica erros internos do servidor", () => {
    expect(
      classificarErroHttp({ status: 500 }),
    ).toBe("ERRO_SERVIDOR");

    expect(
      classificarErroHttp({ status: 503 }),
    ).toBe("ERRO_SERVIDOR");
  });

  it("não classifica erros de transporte como HTTP", () => {
    expect(
      classificarErroHttp(new TypeError("Failed to fetch")),
    ).toBe("OUTRO");
  });

  it("não interpreta erros desconhecidos como expiração de sessão", () => {
    expect(
      classificarErroHttp(new Error("Erro desconhecido")),
    ).toBe("OUTRO");

    expect(
      classificarErroHttp(null),
    ).toBe("OUTRO");
  });
});
