
"use client";

import { useEffect, useState } from "react";

// Acrescente aqui o import existente de useAdminSession
// utilizado nas outras paginas administrativas.

import {
  GradeHorarioResposta,
  TurmaHorario,
  importarGradeHorario,
  listarGradesHorario,
  listarTurmasParaHorarios,
} from "@/lib/grades-horarios-admin";
import { useAdminSession } from "@/contexts/AdminSessionContext";
import Link from "next/dist/client/link";

type PreviaCSV = {
  cabecalho: string[];
  linhas: string[][];
};

function interpretarPrevia(texto: string): PreviaCSV {
  const conteudo = texto.replace(/^\uFEFF/, "");
  const primeiraLinha = conteudo.split(/\r?\n/, 1)[0] ?? "";
  const separador =
    (primeiraLinha.match(/;/g) ?? []).length >
    (primeiraLinha.match(/,/g) ?? []).length
      ? ";"
      : ",";

  const linhas: string[][] = [];
  let linha: string[] = [];
  let campo = "";
  let entreAspas = false;

  for (let i = 0; i < conteudo.length; i++) {
    const caractere = conteudo[i];

    if (caractere === '"') {
      if (entreAspas && conteudo[i + 1] === '"') {
        campo += '"';
        i++;
      } else {
        entreAspas = !entreAspas;
      }
    } else if (caractere === separador && !entreAspas) {
      linha.push(campo.trim());
      campo = "";
    } else if (
      (caractere === "\n" || caractere === "\r") &&
      !entreAspas
    ) {
      if (caractere === "\r" && conteudo[i + 1] === "\n") {
        i++;
      }
      linha.push(campo.trim());

      if (linha.some(Boolean)) {
        linhas.push(linha);
      }

      linha = [];
      campo = "";
    } else {
      campo += caractere;
    }
  }

  linha.push(campo.trim());
  if (linha.some(Boolean)) {
    linhas.push(linha);
  }

  if (entreAspas) {
    throw new Error("CSV com aspas não fechadas.");
  }

  if (linhas.length < 2) {
    throw new Error("O CSV deve conter cabeçalho e horários.");
  }

  return {
    cabecalho: linhas[0],
    linhas: linhas.slice(1),
  };
}

export default function HorariosAdminPage() {
  const sessao = useAdminSession();

  const [turmas, setTurmas] = useState<TurmaHorario[]>([]);
  const [turmaId, setTurmaId] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");

  const [arquivo, setArquivo] = useState<File | null>(null);
  const [previa, setPrevia] = useState<PreviaCSV | null>(null);
  const [grades, setGrades] = useState<GradeHorarioResposta[]>([]);

  const [carregando, setCarregando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");

  const [horaTermino, setHoraTermino] = useState("");

  useEffect(() => {
    let ativo = true;

    async function carregarTurmas() {
      try {
        const dados = await listarTurmasParaHorarios();

        if (ativo) {
          setTurmas(dados.filter((turma) => turma.ativo));
        }
      } catch (error) {
        if (ativo) {
          setErro(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar as turmas.",
          );
        }
      }
    }

    void carregarTurmas();

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!turmaId) {
      setGrades([]);
      return;
    }

    let ativo = true;

    async function carregarGrades() {
      setCarregando(true);

      try {
        const dados = await listarGradesHorario(Number(turmaId));

        if (ativo) {
          setGrades(dados);
        }
      } catch (error) {
        if (ativo) {
          setErro(
            error instanceof Error
              ? error.message
              : "Não foi possível consultar as grades.",
          );
        }
      } finally {
        if (ativo) {
          setCarregando(false);
        }
      }
    }

    void carregarGrades();

    return () => {
      ativo = false;
    };
  }, [turmaId]);

  async function selecionarArquivo(novoArquivo: File | null) {
    setArquivo(null);
    setPrevia(null);
    setErro("");
    setSucesso("");

    if (!novoArquivo) return;

    if (!novoArquivo.name.toLowerCase().endsWith(".csv")) {
      setErro("Selecione um arquivo .csv.");
      return;
    }

    if (novoArquivo.size > 64 * 1024) {
      setErro("O arquivo deve ter no máximo 64 KB.");
      return;
    }

    try {
      const texto = await novoArquivo.text();
      const resultado = interpretarPrevia(texto);

      setArquivo(novoArquivo);
      setPrevia(resultado);
    } catch (error) {
      setErro(
        error instanceof Error
          ? error.message
          : "Não foi possível interpretar o CSV.",
      );
    }
  }

  async function confirmarImportacao() {
    if (!arquivo || !turmaId || !vigenteDesde || !horaTermino || !sessao.csrf_token) {
      setErro("Informe turma, data, arquivo e sessão válida.");
      return;
    }

    if (grades.length > 0) {
        const confirmado = window.confirm(
            "Já existem grades cadastradas para esta turma.\n\n" +
            "A nova importação poderá encerrar a vigência da grade atual. " +
            "O histórico será preservado.\n\n" +
            "Deseja continuar?",
        );

        if (!confirmado) return;
    }

    setErro("");
    setSucesso("");
    setEnviando(true);

    try {
      const resultado = await importarGradeHorario(
        Number(turmaId),
        arquivo,
        vigenteDesde,
        horaTermino,
        sessao.csrf_token,
      );

      const atualizadas = await listarGradesHorario(Number(turmaId));
      setGrades(atualizadas);

      setSucesso(
        `Grade ${resultado.id} importada: ` +
        `${resultado.total_atividades} atividades.`,
      );

      setArquivo(null);
      setPrevia(null);
    } catch (error) {
      setErro(
        error instanceof Error
          ? error.message
          : "Falha ao importar a grade.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
        <Link href="/admin">Voltar ao painel</Link>
      <h1>Grades horárias</h1>
      <p>
        Importe o cronograma semanal de cada turma e controle
        suas versões ao longo do ano letivo.
      </p>

      <section style={{ display: "grid", gap: 12, marginTop: 24 }}>
        <label htmlFor="turma">Turma</label>
        <select
          id="turma"
          value={turmaId}
          onChange={(event) => {
            setTurmaId(event.target.value);
            setErro("");
            setSucesso("");
          }}
        >
          <option value="">Selecione uma turma</option>
          {turmas.map((turma) => (
            <option key={turma.id} value={turma.id}>
              {turma.identificacao} — Ano letivo {turma.ano_letivo_id}
            </option>
          ))}
        </select>

        <label htmlFor="vigente-desde">Início da vigência</label>
        <input
          id="vigente-desde"
          type="date"
          value={vigenteDesde}
          onChange={(event) => setVigenteDesde(event.target.value)}
        />

        <label htmlFor="arquivo">Arquivo CSV</label>
        <input
          id="arquivo"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) =>
            void selecionarArquivo(event.target.files?.[0] ?? null)
          }
        />
        <label htmlFor="hora-termino-grade">Encerramento do último período</label>
        <input
            id="hora-termino-grade"
            type="time"
            required
            value={horaTermino}
            onChange={(event) =>
            setHoraTermino(event.target.value)
            }
        />
      </section>

      {erro && (
        <p role="alert" style={{ color: "crimson", marginTop: 16 }}>
          {erro}
        </p>
      )}

      {sucesso && (
        <p role="status" style={{ color: "green", marginTop: 16 }}>
          {sucesso}
        </p>
      )}

      {previa && (
        <section style={{ marginTop: 28 }}>
          <h2>Pré-visualização do CSV</h2>
          <p>
            {previa.linhas.length} horários encontrados.
            Confira os dados antes de confirmar.
          </p>

          <div style={{ overflowX: "auto" }}>
            <table cellPadding={10} border={1}>
              <thead>
                <tr>
                  {previa.cabecalho.map((titulo, indice) => (
                    <th key={indice}>{titulo}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previa.linhas.map((linha, indice) => (
                  <tr key={indice}>
                    {previa.cabecalho.map((_, coluna) => (
                      <td key={coluna}>
                        {linha[coluna] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Sessão administrativa:{" "}
            {sessao.csrf_token ? "Autenticada" : "Token indisponível"}
          </p>
          <button
            type="button"
            disabled={
              enviando ||
              !turmaId ||
              !vigenteDesde ||
              !arquivo ||
              !horaTermino ||
              !sessao.csrf_token
            }
            onClick={() => void confirmarImportacao()}
            style={{ marginTop: 20, padding: 12 }}
          >
            {enviando
              ? "Importando..."
              : "Confirmar importação"}
          </button>
        </section>
      )}

      <section style={{ marginTop: 36 }}>
        <h2>Histórico de grades da turma</h2>

        {carregando ? (
          <p>Carregando...</p>
        ) : grades.length === 0 ? (
          <p>Nenhuma grade cadastrada para esta turma.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table cellPadding={10} border={1}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Vigente desde</th>
                  <th>Vigente até</th>
                  <th>Atividades</th>
                </tr>
              </thead>
              <tbody>
                {grades.map((grade) => (
                  <tr key={grade.id}>
                    <td>{grade.id}</td>
                    <td>{grade.vigente_desde}</td>
                    <td>{grade.vigente_ate ?? "Atual"}</td>
                    <td>{grade.total_atividades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
