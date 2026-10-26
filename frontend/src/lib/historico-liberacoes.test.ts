
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { consultarHistoricoLiberacoes } from "./historico-liberacoes";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("consultarHistoricoLiberacoes", () => {
  it("consulta o histórico de um aluno", async () => {
    const historico = [
      { id: 1, acao: "LIBERACAO" },
      { id: 2, acao: "CANCELAMENTO" },
    ];

    apiMock.mockResolvedValueOnce(historico);

    const resultado = await consultarHistoricoLiberacoes(15);

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/alunos/15/liberacoes/historico",
    );

    expect(resultado).toEqual(historico);
  });

  it.each([0, -1, 1.5, NaN, Infinity])(
    "rejeita identificador inválido: %s",
    async (alunoId) => {
      await expect(
        consultarHistoricoLiberacoes(alunoId),
      ).rejects.toThrow("Identificador do aluno inválido.");

      expect(apiMock).not.toHaveBeenCalled();
    },
  );

  it("propaga erros retornados pelo cliente HTTP", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Aluno não encontrado."),
    );

    await expect(
      consultarHistoricoLiberacoes(999),
    ).rejects.toThrow("Aluno não encontrado.");
  });
});
