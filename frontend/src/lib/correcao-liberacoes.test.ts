
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { corrigirLiberacaoAdmin } from "./correcao-liberacoes";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("corrigirLiberacaoAdmin", () => {
  it("envia a correção com motivo e CSRF", async () => {
    apiMock.mockResolvedValueOnce({});

    await corrigirLiberacaoAdmin(
      15,
      {
        estado: "CANCELADO",
        motivo: "  Correção solicitada pela escola.  ",
      },
      "csrf-admin",
    );

    expect(apiMock).toHaveBeenCalledWith(
      "/admin/alunos/15/liberacao",
      {
        method: "PATCH",
        csrfToken: "csrf-admin",
        body: JSON.stringify({
          estado: "CANCELADO",
          motivo: "Correção solicitada pela escola.",
        }),
      },
    );
  });

  it("não permite correção sem justificativa", async () => {
    await expect(
      corrigirLiberacaoAdmin(
        15,
        {
          estado: "LIBERADO",
          motivo: "   ",
        },
        "csrf-admin",
      ),
    ).rejects.toThrow("A justificativa é obrigatória.");

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("não permite correção sem token CSRF", async () => {
    await expect(
      corrigirLiberacaoAdmin(
        15,
        {
          estado: "LIBERADO",
          motivo: "Correção administrativa.",
        },
        "",
      ),
    ).rejects.toThrow("Token CSRF não informado.");

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("rejeita identificador inválido", async () => {
    await expect(
      corrigirLiberacaoAdmin(
        0,
        {
          estado: "CANCELADO",
          motivo: "Correção administrativa.",
        },
        "csrf-admin",
      ),
    ).rejects.toThrow("Identificador do aluno inválido.");

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("propaga erros da API", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Operação não permitida."),
    );

    await expect(
      corrigirLiberacaoAdmin(
        15,
        {
          estado: "LIBERADO",
          motivo: "Correção administrativa.",
        },
        "csrf-admin",
      ),
    ).rejects.toThrow("Operação não permitida.");
  });
});
