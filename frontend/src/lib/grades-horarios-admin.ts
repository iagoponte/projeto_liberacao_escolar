
import { apiRequest } from "@/lib/api";

export type TurmaHorario = {
  id: number;
  identificacao: string;
  ano_letivo_id: number;
  ativo: boolean;
};

export type GradeHorarioResposta = {
  id: number;
  turma_id: number;
  vigente_desde: string;
  vigente_ate: string | null;
  horarios: string[];
  hora_termino: string | null;
  total_atividades: number;
};

export function listarTurmasParaHorarios() {
  return apiRequest<TurmaHorario[]>("/admin/turmas");
}

export function listarGradesHorario(turmaId: number) {
  return apiRequest<GradeHorarioResposta[]>(
    `/admin/turmas/${turmaId}/grades`,
  );
}

export async function importarGradeHorario(
  turmaId: number,
  arquivo: File,
  vigenteDesde: string,
  horaTermino: string,
  csrfToken: string,
): Promise<GradeHorarioResposta> {
  const formulario = new FormData();
  formulario.append("arquivo", arquivo);
  formulario.append("vigente_desde", vigenteDesde);
  formulario.append("hora_termino", horaTermino);
  // Utilize a mesma origem configurada em src/lib/api.ts.
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";

  const resposta = await fetch(
    `${apiUrl.replace(/\/$/, "")}/admin/turmas/${turmaId}/grade/importar`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRF-Token": csrfToken,
      },
      body: formulario,
    },
  );

  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => null);

    const detalhe = dados?.detail;

    let mensagem = `Erro HTTP ${resposta.status}.`;

    if (typeof detalhe === "string") {
      mensagem = detalhe;
    } else if (Array.isArray(detalhe)) {
      mensagem = detalhe
        .map((item: { msg?: string }) => item.msg ?? "Dado inválido")
        .join("; ");
    }

    throw new Error(mensagem);
  }

  return (await resposta.json()) as GradeHorarioResposta;
}
