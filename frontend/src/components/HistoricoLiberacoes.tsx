
"use client";

import { useEffect, useState } from "react";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  consultarHistoricoLiberacoes,
  type RegistroHistoricoLiberacao,
  type TipoAcaoHistorico,
} from "@/lib/historico-liberacoes";

interface HistoricoLiberacoesProps {
  alunoId: number;
  nomeAluno: string;
  onClose: () => void;
  onSessaoExpirada?: () => void;
}

const nomesAcoes: Record<TipoAcaoHistorico, string> = {
  LIBERACAO: "Liberação registrada",
  CANCELAMENTO: "Liberação cancelada",
  CORRECAO_ADMIN: "Correção administrativa",
};

function nomeEstado(estado: string | null): string {
  if (estado === null) return "Sem estado anterior";
  if (estado === "LIBERADO") return "Liberado";
  if (estado === "CANCELADO") return "Cancelado";
  return estado;
}

function formatarDataHora(valor: string): string {
  const data = new Date(valor);

  if (Number.isNaN(data.getTime())) {
    return valor;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "America/Fortaleza",
  }).format(data);
}

function formatarHorario(valor: string | null): string {
  return valor ? valor.slice(0, 5) : "—";
}

export default function HistoricoLiberacoes({
  alunoId,
  nomeAluno,
  onClose,
  onSessaoExpirada,
}: HistoricoLiberacoesProps) {
  const [registros, setRegistros] = useState<
    RegistroHistoricoLiberacao[]
  >([]);

  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;

    async function carregarHistorico() {
      setCarregando(true);
      setErro(null);
      setRegistros([]);

      try {
        const resultado =
          await consultarHistoricoLiberacoes(alunoId);

        if (!ativo) return;

        setRegistros(resultado);
      } catch (falha) {
        if (classificarErroHttp(falha) === "NAO_AUTENTICADO") { onSessaoExpirada?.(); return;}
        
        if (!ativo) return;

        setErro(
          falha instanceof Error
            ? falha.message
            : "Não foi possível consultar o histórico.",
        );
      } finally {
        if (ativo) {
          setCarregando(false);
        }
      }
    }

    void carregarHistorico();

    return () => {
      ativo = false;
    };
  }, [alunoId]);

  return (
    <section
      aria-label={`Histórico de ${nomeAluno}`}
      style={{
        marginTop: "24px",
        padding: "24px",
        border: "1px solid #cbd5e1",
        borderRadius: "10px",
        backgroundColor: "#ffffff",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "16px",
        }}
      >
        <div>
          <h2>Histórico de liberações</h2>
          <p>{nomeAluno}</p>
        </div>

        <button type="button" onClick={onClose}>
          Fechar histórico
        </button>
      </div>

      {carregando && (
        <p role="status">Carregando histórico...</p>
      )}

      {erro && <p role="alert">{erro}</p>}

      {!carregando && !erro && registros.length === 0 && (
        <p>Nenhuma alteração registrada para este aluno.</p>
      )}

      {!carregando && !erro && registros.length > 0 && (
        <ol style={{ marginTop: "24px", paddingLeft: "24px" }}>
          {registros.map((registro) => (
            <li
              key={registro.id}
              style={{
                padding: "12px 0",
                borderBottom: "1px solid #e2e8f0",
              }}
            >
              <h3>
                {nomesAcoes[registro.tipo_acao]}
              </h3>

              <p>
                <strong>Quando:</strong>{" "}
                <time dateTime={registro.ocorrido_em}>
                  {formatarDataHora(registro.ocorrido_em)}
                </time>
              </p>

              <p>
                <strong>Autor:</strong>{" "}
                {registro.perfil} — usuário #{registro.usuario_id}
              </p>

              <p>
                <strong>Estado:</strong>{" "}
                {nomeEstado(registro.estado_anterior)}
                {" → "}
                {nomeEstado(registro.novo_estado)}
              </p>

              <p>
                <strong>Horário autorizado:</strong>{" "}
                {formatarHorario(registro.horario_anterior)}
                {" → "}
                {formatarHorario(registro.horario_novo)}
              </p>

              {registro.motivo && (
                <p>
                  <strong>Motivo:</strong> {registro.motivo}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
