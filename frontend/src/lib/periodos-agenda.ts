
export type VisualizacaoAgenda = "semana" | "mes" | "ano";

export interface PeriodoAgenda {
  data_inicio: string;
  data_fim: string;
  titulo: string;
}

function formatarISO(data: Date): string {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");

  return `${ano}-${mes}-${dia}`;
}

export function obterPeriodoAgenda(
  referencia: Date,
  visualizacao: VisualizacaoAgenda,
  deslocamento = 0,
): PeriodoAgenda {
  const ano = referencia.getFullYear();
  const mes = referencia.getMonth();
  const dia = referencia.getDate();

  if (visualizacao === "semana") {
    const referenciaDeslocada = new Date(
      ano,
      mes,
      dia + deslocamento * 7,
    );

    // Segunda-feira como primeiro dia da semana.
    const diaSemana = referenciaDeslocada.getDay();
    const distanciaSegunda = (diaSemana + 6) % 7;

    const inicio = new Date(
      referenciaDeslocada.getFullYear(),
      referenciaDeslocada.getMonth(),
      referenciaDeslocada.getDate() - distanciaSegunda,
    );

    const fim = new Date(
      inicio.getFullYear(),
      inicio.getMonth(),
      inicio.getDate() + 6,
    );

    return {
      data_inicio: formatarISO(inicio),
      data_fim: formatarISO(fim),
      titulo:
        `${inicio.toLocaleDateString("pt-BR")} a ` +
        fim.toLocaleDateString("pt-BR"),
    };
  }

  if (visualizacao === "mes") {
    const inicio = new Date(ano, mes + deslocamento, 1);
    const fim = new Date(ano, mes + deslocamento + 1, 0);

    return {
      data_inicio: formatarISO(inicio),
      data_fim: formatarISO(fim),
      titulo: inicio.toLocaleDateString("pt-BR", {
        month: "long",
        year: "numeric",
      }),
    };
  }

  const anoSelecionado = ano + deslocamento;

  return {
    data_inicio: `${anoSelecionado}-01-01`,
    data_fim: `${anoSelecionado}-12-31`,
    titulo: String(anoSelecionado),
  };
}
