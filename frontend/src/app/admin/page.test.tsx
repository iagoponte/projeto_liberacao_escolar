
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import { listarTurmasAtivas } from "@/lib/turmas";
import AdminPage from "./page";
import { consultarLiberacoesAdmin } from "@/lib/liberacoes-admin";
import { useAdminSession } from "@/contexts/AdminSessionContext";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/liberacoes-admin", () => ({
  consultarLiberacoesAdmin: vi.fn(),
}));

const consultaMock = vi.mocked(consultarLiberacoesAdmin);

beforeEach(() => {
  vi.clearAllMocks();
});

vi.mock("@/lib/turmas", () => ({
  listarTurmasAtivas: vi.fn(),
}));

vi.mock("@/contexts/AdminSessionContext", () => ({
  useAdminSession: vi.fn(),
}));

vi.mock("@/components/CorrecaoLiberacao", () => ({
  default: ({
    onSuccess,
  }: {
    onSuccess: (resultado: {
      aluno_id: number;
      data: string;
      estado: "LIBERADO" | "CANCELADO";
    }) => void;
  }) => (
    <button
      type="button"
      onClick={() =>
        onSuccess({
          aluno_id: 1,
          data: "2026-10-24",
          estado: "CANCELADO",
        })
      }
    >
      Simular correção concluída
    </button>
  ),
}));

vi.mocked(useAdminSession).mockReturnValue({
  usuario: {
    id: 10,
    email: "admin@exemplo.test",
    perfil: "ADMIN",
  },
  csrf_token: "csrf-admin",
});

const turmasMock = vi.mocked(listarTurmasAtivas);

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

describe("Painel administrativo", () => {
  it("consulta e apresenta as liberações de uma turma", async () => {
    consultaMock.mockResolvedValueOnce([
      {
        aluno_id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        turma_id: 3,
        data: "2026-10-20",
        estado: "LIBERADO",
        horario_inicio_liberacao: "16:10:00",
      },
      {
        aluno_id: 2,
        nome_completo: "Pedro Henrique",
        matricula_institucional: "2026002",
        turma_id: 3,
        data: "2026-10-20",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
      },
    ]);

    turmasMock.mockResolvedValueOnce([
      {
        id: 3,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 1,
        turno: "MANHA",
        ativo: true,
      },
    ]);

    render(<AdminPage />);

    const seletor = await screen.findByRole(
      "combobox",
      { name: "Turma" },
    );

    fireEvent.change(seletor, {
      target: { value: "3" },
    });

    fireEvent.change(
      screen.getByLabelText("Data"),
      { target: { value: "2026-10-20" } },
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Consultar" }),
    );

    await waitFor(() => {
      expect(consultaMock).toHaveBeenCalledWith({
        turmaId: 3,
        data: "2026-10-20",
      });
    });

    const tabela = screen.getByRole("table");

    expect(
      await screen.findByText("Ana Beatriz"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Total de alunos"),
    ).toBeInTheDocument();

    // expect(
    //   screen.getByText("Liberados"),
    // ).toBeInTheDocument();

    // expect(
    //   screen.getAllByText("Sem registro"),
    // ).toHaveLength(2);
    expect(
      within(tabela).getByText("Sem registro"),
    ).toBeInTheDocument();

    expect(
      within(tabela).getByText("Liberado"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Exibindo 2 de 2 alunos"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByRole("button", { name: "Ver histórico" }),
    ).toHaveLength(2);
  });

  
  it("filtra a tabela preservando os indicadores gerais", async () => {
    turmasMock.mockResolvedValueOnce([
      {
        id: 3,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 1,
        turno: "MANHA",
        ativo: true,
      },
    ]);

    const alunosGerais = [
      {
        aluno_id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        turma_id: 3,
        data: "2026-10-20",
        estado: "LIBERADO" as const,
        horario_inicio_liberacao: "16:10:00",
      },
      {
        aluno_id: 2,
        nome_completo: "Pedro Henrique",
        matricula_institucional: "2026002",
        turma_id: 3,
        data: "2026-10-20",
        estado: "SEM_REGISTRO" as const,
        horario_inicio_liberacao: null,
      },
    ];

    consultaMock
      .mockResolvedValueOnce(alunosGerais)
      .mockResolvedValueOnce([alunosGerais[0]]);

    render(<AdminPage />);

    const seletorTurma = await screen.findByRole("combobox", {
      name: "Turma",
    });

    fireEvent.change(seletorTurma, {
      target: { value: "3" },
    });

    fireEvent.change(screen.getByLabelText("Data"), {
      target: { value: "2026-10-20" },
    });

    fireEvent.change(screen.getByLabelText("Estado"), {
      target: { value: "LIBERADO" },
    });

    fireEvent.change(screen.getByLabelText("Pesquisar aluno"), {
      target: { value: "  Ana  " },
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Consultar" }),
    );

    await waitFor(() => {
      expect(consultaMock).toHaveBeenCalledTimes(2);
    });

    expect(consultaMock).toHaveBeenCalledWith({
      turmaId: 3,
      data: "2026-10-20",
    });

    expect(consultaMock).toHaveBeenCalledWith({
      turmaId: 3,
      data: "2026-10-20",
      estado: "LIBERADO",
      horario_inicio_liberacao: "16:10:00",
      busca: "Ana",
    });

    expect(
      await screen.findByText("Ana Beatriz"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Pedro Henrique"),
    ).not.toBeInTheDocument();

    expect(
      screen.getByText("Exibindo 1 de 2 alunos"),
    ).toBeInTheDocument();
  });

  
  it("atualiza a consulta após uma correção administrativa", async () => {
    turmasMock.mockResolvedValueOnce([
      {
        id: 3,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 1,
        turno: "MANHA",
        ativo: true,
      },
    ]);

    const alunoLiberado = {
      aluno_id: 1,
      nome_completo: "Ana Beatriz",
      matricula_institucional: "2026001",
      turma_id: 3,
      data: "2026-10-24",
      estado: "LIBERADO" as const,
      horario_inicio_liberacao: "16:10:00",
    };

    const alunoCancelado = {
      ...alunoLiberado,
      estado: "CANCELADO" as const,
      horario_inicio_liberacao: null,
    };

    consultaMock
      .mockResolvedValueOnce([alunoLiberado])
      .mockResolvedValueOnce([alunoCancelado]);

    render(<AdminPage />);

    fireEvent.change(
      await screen.findByRole("combobox", { name: "Turma" }),
      { target: { value: "3" } },
    );

    fireEvent.change(screen.getByLabelText("Data"), {
      target: { value: "2026-10-24" },
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Consultar" }),
    );

    expect(
      await screen.findByText("Ana Beatriz"),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Corrigir liberação",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Simular correção concluída",
      }),
    );

    await waitFor(() => {
      expect(consultaMock).toHaveBeenCalledTimes(2);
    });

    expect(
      await screen.findByText(/Correção do aluno #1 registrada/),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Cancelado", {
        selector: "span",
      }),
    ).toBeInTheDocument();
  });

  
  it("redireciona ao login quando a consulta de turmas retorna 401", async () => {
    turmasMock.mockRejectedValueOnce(
      new ApiError(401, "Sessão expirada."),
    );

    render(<AdminPage />);

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(
      screen.getByText(
        "Sessão expirada. Redirecionando para o login...",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("heading", {
        name: "Liberações escolares",
      }),
    ).not.toBeInTheDocument();
  });


  it("redireciona ao login quando a consulta de liberações retorna 401", async () => {
    turmasMock.mockResolvedValueOnce([
      {
        id: 3,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 1,
        turno: "MANHA",
        ativo: true,
      },
    ]);

    consultaMock.mockRejectedValueOnce(
      new ApiError(401, "Sessão expirada."),
    );

    render(<AdminPage />);

    fireEvent.change(
      await screen.findByRole("combobox", {
        name: "Turma",
      }),
      { target: { value: "3" } },
    );

    fireEvent.change(
      screen.getByLabelText("Data"),
      { target: { value: "2026-10-24" } },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Consultar",
      }),
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(
      screen.getByText(
        "Sessão expirada. Redirecionando para o login...",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("table"),
    ).not.toBeInTheDocument();
  });


  it("apresenta acesso negado sem redirecionar no HTTP 403", async () => {
    turmasMock.mockResolvedValueOnce([
      {
        id: 3,
        identificacao: "1 Ano A",
        ano_escolar: 1,
        ano_letivo_id: 1,
        turno: "MANHA",
        ativo: true,
      },
    ]);

    consultaMock.mockRejectedValueOnce(
      new ApiError(403, "Acesso negado."),
    );

    render(<AdminPage />);

    fireEvent.change(
      await screen.findByRole("combobox", {
        name: "Turma",
      }),
      { target: { value: "3" } },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Consultar",
      }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Você não possui permissão para consultar estas liberações.",
    );

    expect(replaceMock).not.toHaveBeenCalled();

    expect(
      screen.getByRole("heading", {
        name: "Liberações escolares",
      }),
    ).toBeInTheDocument();
  });

});
