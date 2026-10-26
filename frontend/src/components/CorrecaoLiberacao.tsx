
"use client";

import { useState, type FormEvent } from "react";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  corrigirLiberacaoAdmin,
  type EstadoCorrecao,
  type ResultadoCorrecaoLiberacao,
} from "@/lib/correcao-liberacoes";

interface CorrecaoLiberacaoProps {
  alunoId: number;
  nomeAluno: string;
  estadoAtual: EstadoCorrecao | "SEM_REGISTRO";
  csrfToken: string;
  onClose: () => void;
  onSuccess: (resultado: ResultadoCorrecaoLiberacao) => void;
  onSessaoExpirada?: () => void;
}

const nomesEstados = {
  LIBERADO: "Liberado",
  CANCELADO: "Cancelado",
  SEM_REGISTRO: "Sem registro",
};

export default function CorrecaoLiberacao({
  alunoId,
  nomeAluno,
  estadoAtual,
  csrfToken,
  onClose,
  onSuccess,
  onSessaoExpirada,
}: CorrecaoLiberacaoProps) {
  const [novoEstado, setNovoEstado] =
    useState<EstadoCorrecao>(
      estadoAtual === "LIBERADO" ? "CANCELADO" : "LIBERADO",
    );

  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const justificativa = motivo.trim();

  async function confirmar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (salvando) return;

    if (!justificativa) {
      setErro("Informe a justificativa da correção.");
      return;
    }

    if (justificativa.length > 1000) {
      setErro("A justificativa deve ter no máximo 1000 caracteres.");
      return;
    }

    setSalvando(true);
    setErro(null);

    try {
      const resultado = await corrigirLiberacaoAdmin(
        alunoId,
        {
          estado: novoEstado,
          motivo: justificativa,
        },
        csrfToken,
      );

      onSuccess(resultado);
    } catch (falha) {
       if (classificarErroHttp(falha) === "NAO_AUTENTICADO") {
        onSessaoExpirada?.();
        return;
     }
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível corrigir a liberação.",
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section
      aria-label={`Correção de ${nomeAluno}`}
      style={{
        padding: "24px",
        marginTop: "24px",
        border: "1px solid #cbd5e1",
        borderRadius: "10px",
        backgroundColor: "#fff",
      }}
    >
      <h2>Correção administrativa</h2>

      <p>
        <strong>Aluno:</strong> {nomeAluno}
      </p>

      <p>
        <strong>Estado atual:</strong>{" "}
        {nomesEstados[estadoAtual]}
      </p>

      <form onSubmit={confirmar}>
        <fieldset
          disabled={salvando}
          style={{
            border: "none",
            padding: 0,
            marginTop: "20px",
          }}
        >
          <legend>Novo estado</legend>

          <label
            style={{
              display: "block",
              marginTop: "12px",
            }}
          >
            <input
              type="radio"
              name="novo-estado"
              value="LIBERADO"
              checked={novoEstado === "LIBERADO"}
              onChange={() => setNovoEstado("LIBERADO")}
            />
            {" "}Liberado
          </label>

          <label
            style={{
              display: "block",
              marginTop: "8px",
            }}
          >
            <input
              type="radio"
              name="novo-estado"
              value="CANCELADO"
              checked={novoEstado === "CANCELADO"}
              onChange={() => setNovoEstado("CANCELADO")}
            />
            {" "}Cancelado
          </label>
        </fieldset>

        <div style={{ marginTop: "20px" }}>
          <label
            htmlFor="motivo-correcao"
            style={{ display: "block", marginBottom: "8px" }}
          >
            Justificativa da correção
          </label>

          <textarea
            id="motivo-correcao"
            required
            maxLength={1000}
            rows={4}
            value={motivo}
            disabled={salvando}
            onChange={(evento) => setMotivo(evento.target.value)}
            style={{
              display: "block",
              width: "100%",
              padding: "10px",
              border: "1px solid #cbd5e1",
              borderRadius: "6px",
            }}
          />

          <small>{motivo.length}/1000 caracteres</small>
        </div>

        {erro && (
          <p role="alert" style={{ color: "#b42318" }}>
            {erro}
          </p>
        )}

        <div
          style={{
            display: "flex",
            gap: "12px",
            marginTop: "20px",
          }}
        >
          <button
            type="button"
            disabled={salvando}
            onClick={onClose}
          >
            Cancelar
          </button>

          <button
            type="submit"
            disabled={salvando || !justificativa}
          >
            {salvando
              ? "Salvando..."
              : "Confirmar correção"}
          </button>
        </div>
      </form>
    </section>
  );
}
