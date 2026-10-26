
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  ResponsavelSessionProvider,
  useResponsavelSession,
} from "./ResponsavelSessionContext";

const sessao = {
  usuario: {
    id: 8,
    email: "responsavel@exemplo.test",
    perfil: "RESPONSAVEL" as const,
  },
  csrf_token: "csrf-responsavel",
};

function ComponenteTeste() {
  const sessaoAtual = useResponsavelSession();

  return (
    <div>
      <span>{sessaoAtual.usuario.email}</span>
      <span data-testid="csrf">{sessaoAtual.csrf_token}</span>
    </div>
  );
}

describe("ResponsavelSessionContext", () => {
  it("disponibiliza a sessão autenticada aos componentes filhos", () => {
    render(
      <ResponsavelSessionProvider sessao={sessao}>
        <ComponenteTeste />
      </ResponsavelSessionProvider>,
    );

    expect(
      screen.getByText("responsavel@exemplo.test"),
    ).toBeInTheDocument();

    expect(
      screen.getByTestId("csrf"),
    ).toHaveTextContent("csrf-responsavel");
  });

  it("rejeita utilização fora do provider", () => {
    expect(() => {
        render(<ComponenteTeste />);
    }).toThrow("Sessão do responsável não disponível.");
 });
});
