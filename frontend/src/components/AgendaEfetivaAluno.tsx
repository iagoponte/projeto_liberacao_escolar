
"use client";

import { useEffect, useState } from "react";
import { consultarAgendaEfetivaAluno, type AgendaEfetivaAluno as AgendaAluno } from "@/lib/agenda-efetiva-responsavel";
import { ControleLiberacaoHorario } from "@/components/ControleLiberacaoHorario";
import { classificarErroHttp } from "@/lib/erros-http";
import { useRouter } from "next/navigation";

interface Props {
  alunoId: number;
  data: string;
}

const hora = (valor: string) => valor.slice(0, 5);

export function AgendaEfetivaAluno({ alunoId, data }: Props) {
  const { replace } = useRouter();
  const [agenda, setAgenda] = useState<AgendaAluno | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setAgenda(null);
    setErro(null);

    async function carregar() {
      try {
        const resultado = await consultarAgendaEfetivaAluno(alunoId, data);
        if (ativo) setAgenda(resultado);
      } catch (falha) {
        if (!ativo) return;
        if (classificarErroHttp(falha) === "NAO_AUTENTICADO") {
          replace("/login");
          return;
        }
        setErro(falha instanceof Error ? falha.message : "Não foi possível consultar a agenda.");
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    void carregar();
    return () => { ativo = false; };
  }, [alunoId, data, replace]);

  return (
    <section aria-label="Programação efetiva do aluno" style={{ marginTop: 24 }}>
      <h3>Programação escolar</h3>
      {carregando && <p role="status">Carregando programação...</p>}
      {erro && <p role="alert" style={{ color: "#b42318" }}>{erro}</p>}
      {agenda && (
        <>
          <p>Turma #{agenda.turma_id} · {data.split("-").reverse().join("/")}</p>
          {agenda.atividades.length === 0 ? (
            <p>Não há aulas ou atividades programadas para esta data.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr><th scope="col">Início</th><th scope="col">Fim</th><th scope="col">Atividade</th><th scope="col">Tipo</th></tr>
                </thead>
                <tbody>
                  {agenda.atividades.map((atividade, indice) => (
                    <tr key={`${atividade.hora_inicio}-${atividade.evento_id ?? "grade"}-${indice}`}>
                      <td>{hora(atividade.hora_inicio)}</td>
                      <td>{hora(atividade.hora_fim)}</td>
                      <td>{atividade.descricao}</td>
                      <td>{atividade.tipo === "EVENTO" ? "Substituição" : atividade.tipo === "INTERVALO" ? "Intervalo" : "Aula"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {agenda.informativos.length > 0 && (
            <section style={{ marginTop: 20 }}>
              <h4>Avisos da escola</h4>
              <ul>
                {agenda.informativos.map((aviso) => (
                  <li key={aviso.id}>
                    {aviso.titulo}
                    {aviso.hora_inicio && aviso.hora_fim ? ` — ${hora(aviso.hora_inicio)} às ${hora(aviso.hora_fim)}` : ""}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Fora de <table>: o navegador não pode conter um <section> entre <thead> e <tbody>. */}
          <ControleLiberacaoHorario alunoId={alunoId} agenda={agenda} />
        </>
      )}
    </section>
  );
}
