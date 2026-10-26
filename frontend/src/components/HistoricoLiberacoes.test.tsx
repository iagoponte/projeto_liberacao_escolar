
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
} from "@testing-library/react";

import HistoricoLiberacoes from "./HistoricoLiberacoes";

import { consultarHistoricoLiberacoes } from
  "@/lib/historico-liberacoes";

vi.mock("@/lib/historico-liberacoes", () => ({
  consultarHistoricoLiberacoes: vi.fn(),
}));

const historicoMock = vi.mocked(
  consultarHistoricoLiberacoes,
);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("HistoricoLiberacoes", () => {
  it("apresenta as alterações do aluno", async () => {
    historicoMock.mockResolvedValueOnce([
      {
        id: 10,
        liberacao_id: 5,
        aluno_id: 1,
        usuario_id: 8,
        perfil: "RESPONSAVEL",
        ocorrido_em: "2026-10-20T14:30:00Z",
        estado_anterior: null,
        novo_estado: "LIBERADO",
        horario_anterior: null,
        horario_novo: "16:10:00",
        tipo_acao: "LIBERACAO",
        motivo: null,
      },
      {
        id: 11,
        liberacao_id: 5,
        aluno_id: 1,
        usuario_id: 8,
        perfil: "RESPONSAVEL",
        ocorrido_em: "2026-10-20T15:00:00Z",
        estado_anterior: "LIBERADO",
        novo_estado: "CANCELADO",
        horario_anterior: "16:10:00",
        horario_novo: null,
        tipo_acao: "CANCELAMENTO",
        motivo: "Mudança no horário de saída.",
      },
    ]);

    render(
      <HistoricoLiberacoes
        alunoId={1}
        nomeAluno="Ana Beatriz"
        onClose={vi.fn()}
      />,
    );

    expect(
      await screen.findByText("Liberação registrada"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Liberação cancelada"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Ana Beatriz"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/Mudança no horário de saída/),
    ).toBeInTheDocument();

    expect(historicoMock).toHaveBeenCalledWith(1);
  });

  it("informa quando o aluno não possui histórico", async () => {
    historicoMock.mockResolvedValueOnce([]);

    render(
      <HistoricoLiberacoes
        alunoId={2}
        nomeAluno="Pedro Henrique"
        onClose={vi.fn()}
      />,
    );

    expect(
      await screen.findByText(
        "Nenhuma alteração registrada para este aluno.",
      ),
    ).toBeInTheDocument();
  });

  it("permite fechar o histórico", () => {
    historicoMock.mockResolvedValueOnce([]);

    const fecharMock = vi.fn();

    render(
      <HistoricoLiberacoes
        alunoId={1}
        nomeAluno="Ana Beatriz"
        onClose={fecharMock}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Fechar histórico",
      }),
    );

    expect(fecharMock).toHaveBeenCalledOnce();
  });
});
