
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

import CorrecaoLiberacao from "./CorrecaoLiberacao";
import { corrigirLiberacaoAdmin } from "@/lib/correcao-liberacoes";

vi.mock("@/lib/correcao-liberacoes", () => ({
  corrigirLiberacaoAdmin: vi.fn(),
}));

const corrigirMock = vi.mocked(corrigirLiberacaoAdmin);

const propriedades = {
  alunoId: 15,
  nomeAluno: "Ana Beatriz",
  estadoAtual: "LIBERADO" as const,
  csrfToken: "csrf-admin",
  onClose: vi.fn(),
  onSuccess: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CorrecaoLiberacao", () => {
  it("envia a correção e informa o sucesso", async () => {
    const resposta = {
      aluno_id: 15,
      data: "2026-10-24",
      estado: "CANCELADO" as const,
    };

    corrigirMock.mockResolvedValueOnce(resposta);

    render(<CorrecaoLiberacao {...propriedades} />);

    fireEvent.change(
      screen.getByLabelText("Justificativa da correção"),
      {
        target: {
          value: "  Solicitação da coordenação escolar.  ",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Confirmar correção",
      }),
    );

    await waitFor(() => {
      expect(corrigirMock).toHaveBeenCalledWith(
        15,
        {
          estado: "CANCELADO",
          motivo: "Solicitação da coordenação escolar.",
        },
        "csrf-admin",
      );
    });

    await waitFor(() => {
      expect(propriedades.onSuccess).toHaveBeenCalledWith(
        resposta,
      );
    });
  });

  it("exige justificativa para confirmar", () => {
    render(<CorrecaoLiberacao {...propriedades} />);

    const botao = screen.getByRole("button", {
      name: "Confirmar correção",
    });

    expect(botao).toBeDisabled();
    expect(corrigirMock).not.toHaveBeenCalled();
  });

  it("mostra erro quando a API rejeita a correção", async () => {
    corrigirMock.mockRejectedValueOnce(
      new Error("Correção não permitida."),
    );

    render(<CorrecaoLiberacao {...propriedades} />);

    fireEvent.change(
      screen.getByLabelText("Justificativa da correção"),
      {
        target: {
          value: "Correção solicitada pela escola.",
        },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Confirmar correção",
      }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Correção não permitida.");

    expect(propriedades.onSuccess).not.toHaveBeenCalled();
  });
});
