
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import AuthHeader from "./AuthHeader";
import { fazerLogout } from "@/lib/auth";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  fazerLogout: vi.fn(),
}));

const logoutMock = vi.mocked(fazerLogout);

const sessaoAdmin = {
  usuario: {
    id: 1,
    email: "admin@exemplo.test",
    perfil: "ADMIN" as const,
  },
  csrf_token: "csrf-admin",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthHeader", () => {
  it("exibe o usuário autenticado", () => {
    render(<AuthHeader sessao={sessaoAdmin} />);

    expect(
      screen.getByText(/admin@exemplo\.test/),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /sair/i }),
    ).toBeInTheDocument();
  });

  it("encerra a sessão e redireciona ao login", async () => {
    logoutMock.mockResolvedValueOnce(undefined);

    render(<AuthHeader sessao={sessaoAdmin} />);

    fireEvent.click(
      screen.getByRole("button", { name: /sair/i }),
    );

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledWith("csrf-admin");

      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
  });

  it("apresenta erro quando o logout falha", async () => {
    logoutMock.mockRejectedValueOnce(
      new Error("Falha na comunicação."),
    );

    render(<AuthHeader sessao={sessaoAdmin} />);

    fireEvent.click(
      screen.getByRole("button", { name: /sair/i }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Falha na comunicação.");

    expect(replaceMock).not.toHaveBeenCalled();
  });
});
