
import { describe, expect, it } from "vitest";

import { calcularIndicadoresLiberacoes } from "./indicadores-liberacoes";
import type { SituacaoLiberacaoAluno } from "./liberacoes-admin";

describe("calcularIndicadoresLiberacoes", () => {
  it("contabiliza os alunos por estado", () => {
    const alunos: SituacaoLiberacaoAluno[] = [
      {
        aluno_id: 1,
        nome_completo: "Ana",
        matricula_institucional: "001",
        turma_id: 1,
        data: "2026-10-20",
        estado: "LIBERADO",
        horario_inicio_liberacao: "16:10:00",
      },
      {
        aluno_id: 2,
        nome_completo: "Pedro",
        matricula_institucional: "002",
        turma_id: 1,
        data: "2026-10-20",
        estado: "CANCELADO",
        horario_inicio_liberacao: null,
      },
      {
        aluno_id: 3,
        nome_completo: "Mariana",
        matricula_institucional: "003",
        turma_id: 1,
        data: "2026-10-20",
        estado: "SEM_REGISTRO",
        horario_inicio_liberacao: null,
      },
      {
        aluno_id: 4,
        nome_completo: "João",
        matricula_institucional: "004",
        turma_id: 1,
        data: "2026-10-20",
        estado: "LIBERADO",
        horario_inicio_liberacao: "15:30:00",
      },
    ];

    expect(calcularIndicadoresLiberacoes(alunos)).toEqual({
      total: 4,
      liberados: 2,
      cancelados: 1,
      semRegistro: 1,
    });
  });

  it("retorna indicadores zerados para uma turma vazia", () => {
    expect(calcularIndicadoresLiberacoes([])).toEqual({
      total: 0,
      liberados: 0,
      cancelados: 0,
      semRegistro: 0,
    });
  });
});
