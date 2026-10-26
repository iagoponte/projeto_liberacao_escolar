
export type ClassificacaoErroHttp =
  | "NAO_AUTENTICADO"
  | "ACESSO_NEGADO"
  | "VALIDACAO"
  | "ERRO_SERVIDOR"
  | "OUTRO";

interface ErroComStatus {
  status: number;
}

function possuiStatus(
  erro: unknown,
): erro is ErroComStatus {
  return (
    typeof erro === "object" &&
    erro !== null &&
    "status" in erro &&
    typeof erro.status === "number"
  );
}

export function classificarErroHttp(
  erro: unknown,
): ClassificacaoErroHttp {
  if (!possuiStatus(erro)) {
    return "OUTRO";
  }

  switch (erro.status) {
    case 401:
      return "NAO_AUTENTICADO";

    case 403:
      return "ACESSO_NEGADO";

    case 422:
      return "VALIDACAO";

    default:
      if (erro.status >= 500 && erro.status <= 599) {
        return "ERRO_SERVIDOR";
      }

      return "OUTRO";
  }
}
