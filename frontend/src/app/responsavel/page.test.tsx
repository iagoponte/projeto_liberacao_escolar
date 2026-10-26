
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  render,
  screen,
} from "@testing-library/react";

import ResponsavelPage from "./page";
import { listarAlunosResponsavel } from "@/lib/responsavel-alunos";
import { consultarLiberacoesHoje } from "@/lib/liberacoes-responsavel";
import { useResponsavelSession } from "@/contexts/ResponsavelSessionContext";
import { alterarLiberacaoResponsavel } from "@/lib/acoes-liberacao-responsavel";
import { fireEvent, waitFor } from "@testing-library/react";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/responsavel-alunos", () => ({
  listarAlunosResponsavel: vi.fn(),
}));

vi.mock("@/lib/liberacoes-responsavel", () => ({
  consultarLiberacoesHoje: vi.fn(),
}));

vi.mock("@/contexts/ResponsavelSessionContext", () => ({
  useResponsavelSession: vi.fn(),
}));

vi.mock("@/lib/acoes-liberacao-responsavel", () => ({
  alterarLiberacaoResponsavel: vi.fn(),
}));

const liberacoesMock = vi.mocked(consultarLiberacoesHoje);

const listarMock = vi.mocked(listarAlunosResponsavel);

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();

  vi.mocked(useResponsavelSession).mockReturnValue({
  usuario: {
    id: 8,
    email: "responsavel@exemplo.test",
    perfil: "RESPONSAVEL",
  },
  csrf_token: "csrf-responsavel",
});
});

liberacoesMock.mockResolvedValue([]);

describe("Área do responsável", () => {
  it("apresenta os alunos vinculados", async () => {
    listarMock.mockResolvedValueOnce([
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
    ]);

    render(<ResponsavelPage />);

    expect(
      await screen.findByText("Ana Beatriz"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Pedro Henrique"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("2026001"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Matrícula não informada"),
    ).toBeInTheDocument();

    expect(listarMock).toHaveBeenCalledOnce();
  });

  it("informa quando não existem alunos vinculados", async () => {
    listarMock.mockResolvedValueOnce([]);

    render(<ResponsavelPage />);

    expect(
      await screen.findByText(
        "Nenhum aluno vinculado à sua conta.",
      ),
    ).toBeInTheDocument();
  });

  it("apresenta erro quando a consulta falha", async () => {
    listarMock.mockRejectedValueOnce(
      new Error("Não foi possível consultar os alunos."),
    );

    render(<ResponsavelPage />);

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Não foi possível consultar os alunos.",
    );
  });

  
    it("apresenta o estado diário de cada aluno", async () => {
        listarMock.mockResolvedValueOnce([
            {
            id: 1,
            nome_completo: "Ana Beatriz",
            matricula_institucional: "2026001",
            },
            {
            id: 2,
            nome_completo: "Pedro Henrique",
            matricula_institucional: "2026002",
            },
            {
            id: 3,
            nome_completo: "Mariana Costa",
            matricula_institucional: null,
            },
        ]);

        liberacoesMock.mockResolvedValueOnce([
            {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "LIBERADO",
            horario_inicio_liberacao: null,
            },
            {
            aluno_id: 2,
            data: "2026-10-24",
            estado: "CANCELADO",
            horario_inicio_liberacao: null,
            },
            {
            aluno_id: 3,
            data: "2026-10-24",
            estado: "SEM_REGISTRO",
            horario_inicio_liberacao: null,
            },
        ]);

        render(<ResponsavelPage />);

        expect(
            await screen.findByText("Ana Beatriz"),
        ).toBeInTheDocument();

        expect(
            screen.getByText("Pedro Henrique"),
        ).toBeInTheDocument();

        expect(
            screen.getByText("Mariana Costa"),
        ).toBeInTheDocument();

        expect(
            screen.getByText("Liberado"),
        ).toBeInTheDocument();

        expect(
            screen.getByText("Cancelado"),
        ).toBeInTheDocument();

        expect(
            screen.getByText("Sem registro"),
        ).toBeInTheDocument();

        expect(liberacoesMock).toHaveBeenCalledOnce();
    });

    it("não presume ausência de registro quando falta uma situação", async () => {
        listarMock.mockResolvedValueOnce([
            {
            id: 1,
            nome_completo: "Ana Beatriz",
            matricula_institucional: null,
            },
        ]);

        liberacoesMock.mockResolvedValueOnce([]);

        render(<ResponsavelPage />);

        expect(
            await screen.findByText("Estado indisponível"),
        ).toBeInTheDocument();

        expect(
            screen.queryByText("Sem registro"),
        ).not.toBeInTheDocument();
    });

    
    it("autoriza uma liberação e atualiza seu estado", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "SEM_REGISTRO",
            horario_inicio_liberacao: null,
        },
        ])
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "LIBERADO",
            horario_inicio_liberacao: null,
        },
        ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockResolvedValueOnce({
        aluno_id: 1,
        data: "2026-10-24",
        estado: "LIBERADO",
        horario_inicio_liberacao: null,
        });

    render(<ResponsavelPage />);

    expect(
        await screen.findByText("Ana Beatriz"),
    ).toBeInTheDocument();

    fireEvent.click(
        screen.getByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    // Abrir a confirmação não pode alterar o backend.
    expect(alterarLiberacaoResponsavel).not.toHaveBeenCalled();

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    await waitFor(() => {
        expect(alterarLiberacaoResponsavel).toHaveBeenCalledWith(
        1,
        "LIBERAR",
        "csrf-responsavel",
        );
    });

    expect(
        await screen.findByText("Liberado"),
    ).toBeInTheDocument();

    expect(liberacoesMock).toHaveBeenCalledTimes(2);

    expect(
        screen.queryByRole("button", {
        name: "Autorizar liberação",
        }),
    ).not.toBeInTheDocument();
    });

    
    it("não registra liberação quando a confirmação é cancelada", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock.mockResolvedValueOnce([
        {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
        },
    ]);

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", { name: "Voltar" }),
    );

    expect(
        screen.queryByRole("button", {
        name: "Confirmar autorização",
        }),
    ).not.toBeInTheDocument();

    expect(alterarLiberacaoResponsavel).not.toHaveBeenCalled();
    });

    
    it("cancela uma liberação e atualiza seu estado", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "LIBERADO",
            horario_inicio_liberacao: null,
        },
        ])
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "CANCELADO",
            horario_inicio_liberacao: null,
        },
        ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockResolvedValueOnce({
        aluno_id: 1,
        data: "2026-10-24",
        estado: "CANCELADO",
        horario_inicio_liberacao: null,
        });

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Cancelar liberação",
        }),
    );

    // Abrir a confirmação não altera os dados.
    expect(alterarLiberacaoResponsavel).not.toHaveBeenCalled();

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar cancelamento",
        }),
    );

    await waitFor(() => {
        expect(alterarLiberacaoResponsavel).toHaveBeenCalledWith(
        1,
        "CANCELAR",
        "csrf-responsavel",
        );
    });

    expect(
        await screen.findByText("Cancelado"),
    ).toBeInTheDocument();

    expect(liberacoesMock).toHaveBeenCalledTimes(2);

    expect(
        screen.getByRole("button", {
        name: "Autorizar liberação",
        }),
    ).toBeInTheDocument();

    expect(
        screen.queryByRole("button", {
        name: "Cancelar liberação",
        }),
    ).not.toBeInTheDocument();
    });

    
    it("não cancela a liberação quando o responsável desiste", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock.mockResolvedValueOnce([
        {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "LIBERADO",
        horario_inicio_liberacao: null,
        },
    ]);

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Cancelar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Voltar",
        }),
    );

    expect(
        screen.queryByRole("button", {
        name: "Confirmar cancelamento",
        }),
    ).not.toBeInTheDocument();

    expect(alterarLiberacaoResponsavel).not.toHaveBeenCalled();

    expect(
        screen.getByRole("button", {
        name: "Cancelar liberação",
        }),
    ).toBeInTheDocument();
    });
    
    it("preserva o estado confirmado quando a atualização geral falha", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "SEM_REGISTRO",
            horario_inicio_liberacao: null,
        },
        ])
        .mockRejectedValueOnce(
        new Error("Conexão interrompida."),
        );

    vi.mocked(alterarLiberacaoResponsavel)
        .mockResolvedValueOnce({
        aluno_id: 1,
        data: "2026-10-24",
        estado: "LIBERADO",
        horario_inicio_liberacao: null,
        });

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    expect(
        await screen.findByRole("alert"),
    ).toHaveTextContent(
        "A alteração foi confirmada pelo servidor",
    );

    expect(
        screen.getByText("Liberado"),
    ).toBeInTheDocument();

    expect(
        screen.getByRole("button", {
        name: "Cancelar liberação",
        }),
    ).toBeInTheDocument();

    expect(
        screen.queryByRole("button", {
        name: "Autorizar liberação",
        }),
    ).not.toBeInTheDocument();

    expect(
        alterarLiberacaoResponsavel,
    ).toHaveBeenCalledOnce();
    });
    
    it("não altera o estado quando a autorização não é confirmada", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock.mockResolvedValueOnce([
        {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
        },
    ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockRejectedValueOnce(
        new Error("Não foi possível confirmar a operação."),
        );

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    expect(
        await screen.findByRole("alert"),
    ).toHaveTextContent(
        "Não foi possível confirmar a operação.",
    );

    expect(
        screen.getByText("Sem registro"),
    ).toBeInTheDocument();

    expect(
        screen.queryByText("Liberado"),
    ).not.toBeInTheDocument();

    expect(liberacoesMock).toHaveBeenCalledOnce();
    });

    
    it("consulta o estado após falha de transporte no POST", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "SEM_REGISTRO",
            horario_inicio_liberacao: null,
        },
        ])
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "LIBERADO",
            horario_inicio_liberacao: null,
        },
        ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockRejectedValueOnce(
        new TypeError("Failed to fetch"),
        );

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    await waitFor(() => {
        expect(liberacoesMock).toHaveBeenCalledTimes(2);
    });

    expect(
        await screen.findByText("Liberado"),
    ).toBeInTheDocument();

    expect(
        screen.getByText(/Consulta concluída/),
    ).toBeInTheDocument();

    expect(
        alterarLiberacaoResponsavel,
    ).toHaveBeenCalledOnce();
    });

    
    it("bloqueia nova alteração quando não consegue verificar o estado", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock
        .mockResolvedValueOnce([
        {
            aluno_id: 1,
            data: "2026-10-24",
            estado: "SEM_REGISTRO",
            horario_inicio_liberacao: null,
        },
        ])
        .mockRejectedValueOnce(
        new TypeError("Conexão indisponível"),
        );

    vi.mocked(alterarLiberacaoResponsavel)
        .mockRejectedValueOnce(
        new TypeError("Failed to fetch"),
        );

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    expect(
        await screen.findByRole("alert"),
    ).toHaveTextContent(
        "Não foi possível consultar a situação atual",
    );

    expect(
        screen.getByRole("button", {
        name: "Verificar situação",
        }),
    ).toBeInTheDocument();

    expect(
        screen.queryByRole("button", {
        name: "Autorizar liberação",
        }),
    ).not.toBeInTheDocument();

    expect(
        screen.queryByRole("button", {
        name: "Cancelar liberação",
        }),
    ).not.toBeInTheDocument();

    expect(
        alterarLiberacaoResponsavel,
    ).toHaveBeenCalledOnce();
    });

    
    it("redireciona ao login quando o POST retorna 401", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock.mockResolvedValueOnce([
        {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
        },
    ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockRejectedValueOnce(
        new ApiError(401, "Sessão expirada."),
        );

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(
        screen.getByText(/Sessão expirada/),
    ).toBeInTheDocument();

    expect(
        screen.queryByText("Ana Beatriz"),
    ).not.toBeInTheDocument();

    expect(liberacoesMock).toHaveBeenCalledOnce();
    });

    
    it("apresenta acesso negado sem redirecionar no HTTP 403", async () => {
    listarMock.mockResolvedValueOnce([
        {
        id: 1,
        nome_completo: "Ana Beatriz",
        matricula_institucional: "2026001",
        },
    ]);

    liberacoesMock.mockResolvedValueOnce([
        {
        aluno_id: 1,
        data: "2026-10-24",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
        },
    ]);

    vi.mocked(alterarLiberacaoResponsavel)
        .mockRejectedValueOnce(
        new ApiError(403, "Acesso negado."),
        );

    render(<ResponsavelPage />);

    fireEvent.click(
        await screen.findByRole("button", {
        name: "Autorizar liberação",
        }),
    );

    fireEvent.click(
        screen.getByRole("button", {
        name: "Confirmar autorização",
        }),
    );

    expect(
        await screen.findByRole("alert"),
    ).toHaveTextContent(
        "Você não possui permissão para realizar esta operação.",
    );

    expect(replaceMock).not.toHaveBeenCalled();

    expect(
        screen.getByText("Ana Beatriz"),
    ).toBeInTheDocument();

    expect(
        screen.getByText("Sem registro"),
    ).toBeInTheDocument();
    });

});
