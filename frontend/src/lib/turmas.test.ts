
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { listarTurmasAtivas } from "./turmas";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("listarTurmasAtivas", () => {
  it("consulta apenas turmas ativas", async () => {
    const turmas = [
      {
        id: 1,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 2,
        turno: "MANHA",
        ativo: true,
      },
    ];

    apiMock.mockResolvedValueOnce(turmas);

    const resultado = await listarTurmasAtivas();

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/turmas?ativo=true",
    );

    expect(resultado).toEqual(turmas);
  });
});
