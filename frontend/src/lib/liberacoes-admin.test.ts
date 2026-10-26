
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { consultarLiberacoesAdmin } from "./liberacoes-admin";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("consultarLiberacoesAdmin", () => {
  it("consulta liberações por turma e data", async () => {
    const registros = [
      {
        aluno_id: 1,
        nome_completo: "Ana",
        matricula_institucional: "2026001",
        turma_id: 2,
        data: "2026-10-20",
        estado: "LIBERADO" as const,
      },
    ];

    apiMock.mockResolvedValueOnce(registros);

    const resultado = await consultarLiberacoesAdmin({
      turmaId: 2,
      data: "2026-10-20",
    });

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/liberacoes?turma_id=2&data=2026-10-20",
    );

    expect(resultado).toEqual(registros);
  });

  it("aplica o filtro de estado", async () => {
    apiMock.mockResolvedValueOnce([]);

    await consultarLiberacoesAdmin({
      turmaId: 3,
      data: "2026-10-20",
      estado: "CANCELADO",
    });

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/liberacoes?turma_id=3&data=2026-10-20&estado=CANCELADO",
    );
  });

  it("codifica a pesquisa por nome", async () => {
    apiMock.mockResolvedValueOnce([]);

    await consultarLiberacoesAdmin({
      turmaId: 1,
      data: "2026-10-20",
      busca: "  Ana Maria  ",
    });

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/liberacoes?turma_id=1&data=2026-10-20&busca=Ana+Maria",
    );
  });

  it("ignora pesquisas vazias", async () => {
    apiMock.mockResolvedValueOnce([]);

    await consultarLiberacoesAdmin({
      turmaId: 1,
      data: "2026-10-20",
      busca: "   ",
    });

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/liberacoes?turma_id=1&data=2026-10-20",
    );
  });
});
