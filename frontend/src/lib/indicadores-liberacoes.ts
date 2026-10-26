
import type { SituacaoLiberacaoAluno } from "./liberacoes-admin";

export interface IndicadoresLiberacoes {
  total: number;
  liberados: number;
  cancelados: number;
  semRegistro: number;
}

export function calcularIndicadoresLiberacoes(
  alunos: SituacaoLiberacaoAluno[],
): IndicadoresLiberacoes {
  return alunos.reduce<IndicadoresLiberacoes>(
    (indicadores, aluno) => {
      indicadores.total += 1;

      switch (aluno.estado) {
        case "LIBERADO":
          indicadores.liberados += 1;
          break;

        case "CANCELADO":
          indicadores.cancelados += 1;
          break;

        case "SEM_REGISTRO":
          indicadores.semRegistro += 1;
          break;
      }

      return indicadores;
    },
    {
      total: 0,
      liberados: 0,
      cancelados: 0,
      semRegistro: 0,
    },
  );
}
