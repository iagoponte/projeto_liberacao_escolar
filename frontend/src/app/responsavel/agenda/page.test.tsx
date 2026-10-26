
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import AgendaResponsavelPage from "./page";
import { consultarAgendaResponsavel } from "@/lib/agenda-responsavel";
import { obterPeriodoAgenda } from "@/lib/periodos-agenda";
import { ApiError } from "@/lib/api";

vi.mock("@/lib/agenda-responsavel", () => ({
  consultarAgendaResponsavel: vi.fn(),
}));

const agendaMock = vi.mocked(consultarAgendaResponsavel);

beforeEach(() => {
  vi.clearAllMocks();
  agendaMock.mockResolvedValue([]);
});

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));


describe("Agenda escolar do responsável", () => {
  it("consulta o mês atual e apresenta os eventos ordenados", async () => {
    agendaMock.mockResolvedValueOnce([
      {
        id: 2,
        turma_id: 5,
        titulo: "Feira de Ciências",
        data_inicio: "2026-11-20",
        data_fim: "2026-11-21",
        ativo: true,
      },
      {
        id: 1,
        turma_id: 3,
        titulo: "Reunião de responsáveis",
        data_inicio: "2026-11-10",
        data_fim: "2026-11-10",
        ativo: true,
      },
    ]);

    render(<AgendaResponsavelPage />);

    const secao = await screen.findByRole("region", {
      name: "Eventos escolares",
    });

    const eventos = within(secao).getAllByRole("article");

    expect(eventos).toHaveLength(2);

    expect(
      within(eventos[0]).getByText("Reunião de responsáveis"),
    ).toBeInTheDocument();

    expect(
      within(eventos[1]).getByText("Feira de Ciências"),
    ).toBeInTheDocument();

    expect(screen.getByText("10/11/2026")).toBeInTheDocument();

    expect(
      screen.getByText("20/11/2026 a 21/11/2026"),
    ).toBeInTheDocument();

    const periodo = obterPeriodoAgenda(new Date(), "mes");

    expect(agendaMock).toHaveBeenCalledWith({
      data_inicio: periodo.data_inicio,
      data_fim: periodo.data_fim,
    });
  });

  it("informa quando o período não contém eventos", async () => {
    render(<AgendaResponsavelPage />);

    expect(
      await screen.findByText(
        "Nenhum evento escolar encontrado neste período.",
      ),
    ).toBeInTheDocument();
  });

  it("apresenta erros da consulta", async () => {
    agendaMock.mockRejectedValueOnce(
      new Error("Falha ao carregar eventos."),
    );

    render(<AgendaResponsavelPage />);

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Falha ao carregar eventos.");
  });

  it("navega para o mês seguinte", async () => {
    render(<AgendaResponsavelPage />);

    await waitFor(() => {
      expect(agendaMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Próximo" }),
    );

    const proximoMes = obterPeriodoAgenda(
      new Date(),
      "mes",
      1,
    );

    await waitFor(() => {
      expect(agendaMock).toHaveBeenLastCalledWith({
        data_inicio: proximoMes.data_inicio,
        data_fim: proximoMes.data_fim,
      });
    });
  });

  it("alterna para a visualização semanal", async () => {
    render(<AgendaResponsavelPage />);

    fireEvent.click(
      screen.getByRole("button", { name: "Semana" }),
    );

    const semana = obterPeriodoAgenda(
      new Date(),
      "semana",
    );

    await waitFor(() => {
      expect(agendaMock).toHaveBeenLastCalledWith({
        data_inicio: semana.data_inicio,
        data_fim: semana.data_fim,
      });
    });

    expect(
      screen.getByRole("button", { name: "Semana" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("alterna para a visualização anual", async () => {
    render(<AgendaResponsavelPage />);

    fireEvent.click(
      screen.getByRole("button", { name: "Ano" }),
    );

    const ano = obterPeriodoAgenda(new Date(), "ano");

    await waitFor(() => {
      expect(agendaMock).toHaveBeenLastCalledWith({
        data_inicio: ano.data_inicio,
        data_fim: ano.data_fim,
      });
    });
  });

  it("retorna ao período atual", async () => {
    render(<AgendaResponsavelPage />);

    fireEvent.click(
      screen.getByRole("button", { name: "Anterior" }),
    );

    const anterior = obterPeriodoAgenda(
      new Date(),
      "mes",
      -1,
    );

    await waitFor(() => {
      expect(agendaMock).toHaveBeenCalledWith({
        data_inicio: anterior.data_inicio,
        data_fim: anterior.data_fim,
      });
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Período atual" }),
    );

    const atual = obterPeriodoAgenda(new Date(), "mes");

    await waitFor(() => {
      expect(agendaMock).toHaveBeenLastCalledWith({
        data_inicio: atual.data_inicio,
        data_fim: atual.data_fim,
      });
    });
  });

  
    it("redireciona ao login quando a agenda retorna 401", async () => {
    agendaMock.mockRejectedValueOnce(
        new ApiError(401, "Sessão expirada."),
    );

    render(<AgendaResponsavelPage />);

    await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(
        screen.getByText(
        "Sessão expirada. Redirecionando para o login...",
        ),
    ).toBeInTheDocument();

    expect(
        screen.queryByRole("region", {
        name: "Eventos escolares",
        }),
    ).not.toBeInTheDocument();

    expect(
        screen.queryByRole("button", {
        name: "Próximo",
        }),
    ).not.toBeInTheDocument();
    });


    it("apresenta acesso negado sem redirecionar no HTTP 403", async () => {
    agendaMock.mockRejectedValueOnce(
        new ApiError(403, "Acesso negado."),
    );

    render(<AgendaResponsavelPage />);

    expect(
        await screen.findByRole("alert"),
    ).toHaveTextContent(
        "Você não possui permissão para consultar a agenda escolar.",
    );

    expect(replaceMock).not.toHaveBeenCalled();

    expect(
        screen.getByRole("heading", {
        name: "Agenda escolar",
        }),
    ).toBeInTheDocument();
    });

    
    it("identifica sessão expirada ao navegar entre períodos", async () => {
    agendaMock
        .mockResolvedValueOnce([])
        .mockRejectedValueOnce(
        new ApiError(401, "Sessão expirada."),
        );

    render(<AgendaResponsavelPage />);

    expect(
        await screen.findByText(
        "Nenhum evento escolar encontrado neste período.",
        ),
    ).toBeInTheDocument();

    fireEvent.click(
        screen.getByRole("button", {
        name: "Próximo",
        }),
    );

    await waitFor(() => {
        expect(replaceMock).toHaveBeenCalledWith("/login");
    });

    expect(agendaMock).toHaveBeenCalledTimes(2);

    expect(
        screen.queryByText(
        "Nenhum evento escolar encontrado neste período.",
        ),
    ).not.toBeInTheDocument();
    });

});
