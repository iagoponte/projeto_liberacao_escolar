"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AgendaEfetivaAluno } from "@/components/AgendaEfetivaAluno";
import { listarAlunosResponsavel, type AlunoResponsavel } from "@/lib/responsavel-alunos";
import { classificarErroHttp } from "@/lib/erros-http";

function hojeNaEscola(): string {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const valores = Object.fromEntries(partes.map((parte) => [parte.type, parte.value]));
  return `${valores.year}-${valores.month}-${valores.day}`;
}

export default function AgendaResponsavelPage() {
  const { replace } = useRouter();
  const [alunos, setAlunos] = useState<AlunoResponsavel[]>([]);
  const [alunoId, setAlunoId] = useState("");
  const [data, setData] = useState(hojeNaEscola);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const resultado = await listarAlunosResponsavel();
        if (!ativo) return;
        setAlunos(resultado);
        setAlunoId((anterior) => anterior || (resultado[0] ? String(resultado[0].id) : ""));
      } catch (falha) {
        if (!ativo) return;
        if (classificarErroHttp(falha) === "NAO_AUTENTICADO") {
          setSessaoExpirada(true);
          replace("/login");
          return;
        }
        setErro(falha instanceof Error ? falha.message : "Não foi possível listar os alunos.");
      } finally {
        if (ativo) setCarregando(false);
      }
    }
    void carregar();
    return () => { ativo = false; };
  }, [replace]);

  if (sessaoExpirada) return <main role="status">Sessão expirada. Redirecionando...</main>;

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 32 }}>
      <Link href="/responsavel">Voltar para meus alunos</Link>
      <h1>Agenda escolar</h1>
      <p>Consulte aulas, intervalos, provas substitutivas e comunicados de cada aluno.</p>

      {carregando && <p role="status">Carregando alunos...</p>}
      {erro && <p role="alert" style={{ color: "#b42318" }}>{erro}</p>}
      {!carregando && !erro && alunos.length === 0 && <p>Nenhum aluno vinculado à sua conta.</p>}

      {!carregando && alunos.length > 0 && (
        <>
          <section style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 24 }}>
            <div>
              <label htmlFor="aluno-agenda">Aluno</label>
              <select id="aluno-agenda" value={alunoId} onChange={(event) => setAlunoId(event.target.value)}>
                {alunos.map((aluno) => <option key={aluno.id} value={aluno.id}>{aluno.nome_completo}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="data-agenda">Data da programação</label>
              <input id="data-agenda" type="date" value={data} onChange={(event) => setData(event.target.value)} />
            </div>
            <button type="button" onClick={() => setData(hojeNaEscola())}>Hoje</button>
          </section>

          {alunoId && data && <AgendaEfetivaAluno alunoId={Number(alunoId)} data={data} />}
        </>
      )}
    </main>
  );
}

