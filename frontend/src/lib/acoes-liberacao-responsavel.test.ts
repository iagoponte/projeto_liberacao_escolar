
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./api";
import { alterarLiberacaoResponsavel } from "./acoes-liberacao-responsavel";

vi.mock("./api", () => ({
  apiRequest: vi.fn(),
}));

const apiMock = vi.mocked(apiRequest);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("alterarLiberacaoResponsavel", () => {
  it("envia a autorização de liberação com CSRF", async () => {
    const resposta = {
      aluno_id: 15,
      data: "2026-10-24",
      estado: "LIBERADO" as const,
    };

    apiMock.mockResolvedValueOnce(resposta);

    const resultado = await alterarLiberacaoResponsavel(
      15,
      "LIBERAR",
      "csrf-responsavel",
    );

    expect(apiMock).toHaveBeenCalledWith(
      "/responsavel/alunos/15/liberacao",
      {
        method: "POST",
        csrfToken: "csrf-responsavel",
        body: JSON.stringify({ acao: "LIBERAR" }),
      },
    );

    expect(resultado).toEqual(resposta);
  });

  it("envia o cancelamento utilizando o mesmo endpoint", async () => {
    apiMock.mockResolvedValueOnce({
      aluno_id: 15,
      data: "2026-10-24",
      estado: "CANCELADO",
    });

    await alterarLiberacaoResponsavel(
      15,
      "CANCELAR",
      "csrf-responsavel",
    );

    expect(apiMock).toHaveBeenCalledWith(
      "/responsavel/alunos/15/liberacao",
      {
        method: "POST",
        csrfToken: "csrf-responsavel",
        body: JSON.stringify({ acao: "CANCELAR" }),
      },
    );
  });

  it("rejeita identificador inválido", async () => {
    await expect(
      alterarLiberacaoResponsavel(
        0,
        "LIBERAR",
        "csrf-responsavel",
      ),
    ).rejects.toThrow("Identificador do aluno inválido.");

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("rejeita ausência de CSRF", async () => {
    await expect(
      alterarLiberacaoResponsavel(
        15,
        "LIBERAR",
        "",
      ),
    ).rejects.toThrow("Token CSRF não informado.");

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("propaga erros da API", async () => {
    apiMock.mockRejectedValueOnce(
      new Error("Operação não permitida."),
    );

    await expect(
      alterarLiberacaoResponsavel(
        15,
        "LIBERAR",
        "csrf-responsavel",
      ),
    ).rejects.toThrow("Operação não permitida.");
  });
});
