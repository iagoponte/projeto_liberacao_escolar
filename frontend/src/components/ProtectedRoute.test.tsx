
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  render,
  screen,
  waitFor,
  cleanup,
} from "@testing-library/react";

import ProtectedRoute from "./ProtectedRoute";
import { obterSessao } from "@/lib/auth";
import { ApiError } from "@/lib/api";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

vi.mock("@/lib/auth", () => ({
  obterSessao: vi.fn(),
}));

const sessaoMock = vi.mocked(obterSessao);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("ProtectedRoute", () => {
  it("permite acesso ao perfil correto", async () => {
    sessaoMock.mockResolvedValueOnce({
      usuario: {
        id: 1,
        email: "admin@exemplo.test",
        perfil: "ADMIN",
      },
      csrf_token: "csrf-admin",
    });

    render(
      <ProtectedRoute perfilPermitido="ADMIN">
        <h1>Painel administrativo</h1>
      </ProtectedRoute>,
    );

    screen.debug();

    expect(
      await screen.findByText("Painel administrativo"),
    ).toBeInTheDocument();

    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redireciona usuário sem sessão ao login", async () => {
    sessaoMock.mockRejectedValueOnce(
      new ApiError(401, "Sessao nao autenticada."),
    );

    render(
      <ProtectedRoute perfilPermitido="ADMIN">
        <h1>Conteúdo restrito</h1>
      </ProtectedRoute>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(
      screen.queryByText("Conteúdo restrito"),
    ).not.toBeInTheDocument();
  });

  it("redireciona usuário com perfil incorreto", async () => {
    sessaoMock.mockResolvedValueOnce({
      usuario: {
        id: 2,
        email: "responsavel@exemplo.test",
        perfil: "RESPONSAVEL",
      },
      csrf_token: "csrf-responsavel",
    });

    render(
      <ProtectedRoute perfilPermitido="ADMIN">
        <h1>Conteúdo administrativo</h1>
      </ProtectedRoute>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/responsavel");
    });

    expect(
      screen.queryByText("Conteúdo administrativo"),
    ).not.toBeInTheDocument();
  });
});
