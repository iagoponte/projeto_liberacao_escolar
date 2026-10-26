
import { describe, expect, it } from "vitest";
import { obterPeriodoAgenda } from "./periodos-agenda";

describe("obterPeriodoAgenda", () => {
  const referencia = new Date(2026, 9, 24);

  it("calcula a semana de segunda a domingo", () => {
    expect(obterPeriodoAgenda(referencia, "semana")).toMatchObject({
      data_inicio: "2026-10-19",
      data_fim: "2026-10-25",
    });
  });

  it("avança e retrocede semanas", () => {
    expect(
      obterPeriodoAgenda(referencia, "semana", 1).data_inicio,
    ).toBe("2026-10-26");

    expect(
      obterPeriodoAgenda(referencia, "semana", -1).data_inicio,
    ).toBe("2026-10-12");
  });

  it("calcula corretamente o mês", () => {
    expect(obterPeriodoAgenda(referencia, "mes")).toMatchObject({
      data_inicio: "2026-10-01",
      data_fim: "2026-10-31",
    });
  });

  it("atravessa corretamente os limites do ano", () => {
    expect(obterPeriodoAgenda(referencia, "mes", 3)).toMatchObject({
      data_inicio: "2027-01-01",
      data_fim: "2027-01-31",
    });
  });

  it("considera fevereiro de ano bissexto", () => {
    expect(
      obterPeriodoAgenda(new Date(2028, 1, 15), "mes"),
    ).toMatchObject({
      data_inicio: "2028-02-01",
      data_fim: "2028-02-29",
    });
  });

  it("calcula o intervalo anual", () => {
    expect(obterPeriodoAgenda(referencia, "ano", 1)).toMatchObject({
      data_inicio: "2027-01-01",
      data_fim: "2027-12-31",
      titulo: "2027",
    });
  });
});
