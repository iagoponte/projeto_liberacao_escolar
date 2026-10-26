
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { consultarAgendaResponsavel } from "./agenda-responsavel";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("consultarAgendaResponsavel", () => {
  it("consulta a agenda do responsável autenticado", async () => {
    apiMock.mockResolvedValueOnce([]);

    const resultado = await consultarAgendaResponsavel();

    expect(apiMock).toHaveBeenCalledOnce();

    expect(apiMock).toHaveBeenCalledWith(
    "/responsavel/agenda",
    );

    expect(resultado).toEqual([]);
  });

  it("propaga erros da API", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Não foi possível consultar a agenda."),
    );

    await expect(
      consultarAgendaResponsavel(),
    ).rejects.toThrow(
      "Não foi possível consultar a agenda.",
    );
  });

  
    it("envia corretamente os filtros de período", async () => {
    apiMock.mockResolvedValueOnce([]);

    await consultarAgendaResponsavel({
        data_inicio: "2026-10-01",
        data_fim: "2026-10-31",
    });

    expect(apiMock).toHaveBeenCalledWith(
        "/responsavel/agenda?data_inicio=2026-10-01&data_fim=2026-10-31",
    );
    });

});
