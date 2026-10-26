"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listarAlunosResponsavel, type AlunoResponsavel } from "@/lib/responsavel-alunos";
import { consultarLiberacoesHoje, type SituacaoLiberacaoResponsavel } from "@/lib/liberacoes-responsavel";
import { classificarErroHttp } from "@/lib/erros-http";

export default function ResponsavelPage() {
  const { replace } = useRouter();
  const [alunos, setAlunos] = useState<AlunoResponsavel[]>([]);
  const [situacoes, setSituacoes] = useState<SituacaoLiberacaoResponsavel[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const [alunosObtidos, liberacoesObtidas] = await Promise.all([
          listarAlunosResponsavel(), consultarLiberacoesHoje(),
        ]);
        if (!ativo) return;
        setAlunos(alunosObtidos);
        setSituacoes(liberacoesObtidas);
      } catch (falha) {
        if (!ativo) return;
        if (classificarErroHttp(falha) === "NAO_AUTENTICADO") {
          setSessaoExpirada(true);
          replace("/login");
          return;
        }
        setErro(falha instanceof Error ? falha.message : "Não foi possível consultar seus alunos.");
      } finally {
        if (ativo) setCarregando(false);
      }
    }
    void carregar();
    return () => { ativo = false; };
  }, [replace]);

  if (sessaoExpirada) return <main role="status">Sessão expirada. Redirecionando...</main>;

  const porAluno = new Map(situacoes.map((situacao) => [situacao.aluno_id, situacao]));

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 32 }}>
      <h1>Meus alunos</h1>
      <p>Visualize as liberações registradas hoje. Para consultar aulas e autorizar a saída por horário, acesse a agenda escolar.</p>
      <p><Link href="/responsavel/agenda">Consultar agenda escolar e autorizar saída</Link></p>

      {carregando && <p role="status">Carregando alunos...</p>}
      {erro && <p role="alert" style={{ color: "#b42318" }}>{erro}</p>}
      {!carregando && !erro && alunos.length === 0 && <p>Nenhum aluno vinculado à sua conta.</p>}

      {!carregando && !erro && alunos.length > 0 && (
        <section aria-label="Alunos vinculados" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16, marginTop: 24 }}>
          {alunos.map((aluno) => {
            const situacao = porAluno.get(aluno.id);
            const estado = situacao?.estado ?? "SEM_REGISTRO";
            const horario = situacao?.horario_inicio_liberacao;
            return (
              <article key={aluno.id} style={{ padding: 20, border: "1px solid #cbd5e1", borderRadius: 10 }}>
                <h2>{aluno.nome_completo}</h2>
                <p><strong>Matrícula: </strong>{aluno.matricula_institucional || "Não informada"}</p>
                <p><strong>Liberação de hoje: </strong>{estado === "LIBERADO" ? "Liberado" : estado === "CANCELADO" ? "Cancelado" : "Sem registro"}</p>
                {estado === "LIBERADO" && <p><strong>A partir de: </strong>{horario ? horario.slice(0, 5) : "Horário não definido"}</p>}
                <Link href="/responsavel/agenda">Ver agenda e gerenciar liberação</Link>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}

