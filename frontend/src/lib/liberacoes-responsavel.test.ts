
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { consultarLiberacoesHoje } from "./liberacoes-responsavel";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("consultarLiberacoesHoje", () => {
  it("consulta os estados da data escolar atual", async () => {
    const situacoes = [
      {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "LIBERADO" as const,
      },
      {
        aluno_id: 2,
        data: "2026-10-24",
        estado: "SEM_REGISTRO" as const,
      },
    ];

    apiMock.mockResolvedValueOnce(situacoes);

    const resultado = await consultarLiberacoesHoje();

    expect(apiMock).toHaveBeenCalledWith(
      "/responsavel/liberacoes/hoje",
    );

    expect(resultado).toEqual(situacoes);
  });

  it("propaga erros da API", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Não foi possível consultar as liberações."),
    );

    await expect(
      consultarLiberacoesHoje(),
    ).rejects.toThrow(
      "Não foi possível consultar as liberações.",
    );
  });
});
