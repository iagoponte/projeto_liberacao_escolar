
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  fazerLogin,
  obterSessao,
  fazerLogout,
} from "./auth";

import { apiRequest } from "./api";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Autenticação", () => {
  it("envia email e senha para o login", async () => {
    const sessao = {
      usuario: {
        id: 1,
        email: "admin@exemplo.test",
        perfil: "ADMIN" as const,
      },
      csrf_token: "csrf-teste",
    };

    apiMock.mockResolvedValueOnce(sessao);

    const resultado = await fazerLogin({
      email: "admin@exemplo.test",
      senha: "senha-teste",
    });

    expect(apiMock).toHaveBeenCalledWith(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({
          email: "admin@exemplo.test",
          senha: "senha-teste",
        }),
      },
    );

    expect(resultado).toEqual(sessao);
  });

  it("recupera a sessão autenticada", async () => {
    const sessao = {
      usuario: {
        id: 2,
        email: "responsavel@exemplo.test",
        perfil: "RESPONSAVEL" as const,
      },
      csrf_token: "csrf-responsavel",
    };

    apiMock.mockResolvedValueOnce(sessao);

    const resultado = await obterSessao();

    expect(apiMock).toHaveBeenCalledWith(
      "/auth/me",
    );

    expect(resultado).toEqual(sessao);
  });

  it("envia o CSRF ao encerrar a sessão", async () => {
    apiMock.mockResolvedValueOnce(undefined);

    await fazerLogout("csrf-teste");

    expect(apiMock).toHaveBeenCalledWith(
      "/auth/logout",
      {
        method: "POST",
        csrfToken: "csrf-teste",
      },
    );
  });
});
