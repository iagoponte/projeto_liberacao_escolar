
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import LoginPage from "./page";
import { fazerLogin } from "@/lib/auth";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  fazerLogin: vi.fn(),
}));

const loginMock = vi.mocked(fazerLogin);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Página de login", () => {
  it("exibe os campos de autenticação", () => {
    render(<LoginPage />);

    expect(
      screen.getByLabelText(/email/i),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText(/senha/i),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /entrar/i }),
    ).toBeInTheDocument();
  });

  it("autentica administrador e redireciona", async () => {
    loginMock.mockResolvedValueOnce({
      usuario: {
        id: 1,
        email: "admin@exemplo.test",
        perfil: "ADMIN",
      },
      csrf_token: "csrf-admin",
    });

    render(<LoginPage />);

    fireEvent.change(
      screen.getByLabelText(/email/i),
      {
        target: { value: "admin@exemplo.test" },
      },
    );

    fireEvent.change(
      screen.getByLabelText(/senha/i),
      {
        target: { value: "senha-teste" },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: /entrar/i }),
    );

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "admin@exemplo.test",
        senha: "senha-teste",
      });

      expect(pushMock).toHaveBeenCalledWith("/admin");
    });
  });

  it("redireciona responsável para sua área", async () => {
    loginMock.mockResolvedValueOnce({
      usuario: {
        id: 2,
        email: "responsavel@exemplo.test",
        perfil: "RESPONSAVEL",
      },
      csrf_token: "csrf-responsavel",
    });

    render(<LoginPage />);

    fireEvent.change(
      screen.getByLabelText(/email/i),
      {
        target: { value: "responsavel@exemplo.test" },
      },
    );

    fireEvent.change(
      screen.getByLabelText(/senha/i),
      {
        target: { value: "senha-teste" },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: /entrar/i }),
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/responsavel");
    });
  });

  it("apresenta mensagem para credenciais inválidas", async () => {
    loginMock.mockRejectedValueOnce(
      new Error("Credenciais invalidas."),
    );

    render(<LoginPage />);

    fireEvent.change(
      screen.getByLabelText(/email/i),
      {
        target: { value: "erro@exemplo.test" },
      },
    );

    fireEvent.change(
      screen.getByLabelText(/senha/i),
      {
        target: { value: "senha-errada" },
      },
    );

    fireEvent.click(
      screen.getByRole("button", { name: /entrar/i }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Credenciais invalidas.");

    expect(pushMock).not.toHaveBeenCalled();
  });
});
