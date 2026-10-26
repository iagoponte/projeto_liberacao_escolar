
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { listarAlunosResponsavel } from "./responsavel-alunos";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("listarAlunosResponsavel", () => {
  it("consulta os alunos da sessão autenticada", async () => {
    const alunos = [
        {
            id: 1,
            nome_completo: "Ana Beatriz",
            matricula_institucional: "2026001",
        },
        {
            id: 2,
            nome_completo: "Pedro Henrique",
            matricula_institucional: null,
        },
    ];

    apiMock.mockResolvedValueOnce(alunos);

    const resultado = await listarAlunosResponsavel();

    expect(apiMock).toHaveBeenCalledWith(
      "/responsavel/alunos",
    );

    expect(resultado).toEqual(alunos);
  });

  it("retorna uma lista vazia quando não há alunos", async () => {
    apiMock.mockResolvedValueOnce([]);

    const resultado = await listarAlunosResponsavel();

    expect(resultado).toEqual([]);
  });

  it("propaga erros de autenticação da API", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Sessão não autenticada."),
    );

    await expect(
      listarAlunosResponsavel(),
    ).rejects.toThrow("Sessão não autenticada.");
  });
});
