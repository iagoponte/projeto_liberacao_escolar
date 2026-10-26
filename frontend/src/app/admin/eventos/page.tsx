
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import { useAdminSession } from "@/contexts/AdminSessionContext";
import { classificarErroHttp } from "@/lib/erros-http";

import {
  listarAnosLetivos,
  type AnoLetivo,
} from "@/lib/anos-letivos-admin";

import {
  listarTurmasAdmin,
  type TurmaAdmin,
} from "@/lib/turmas-admin";

import {
  listarEventosAdmin,
  criarEventoAdmin,
  atualizarEventoAdmin,
  desativarEventoAdmin,
  formatarHorarioEvento,
  obterDescricaoModoEvento,
  type DadosEvento,
  type EventoAdmin,
  type ModoAplicacaoEvento,
} from "@/lib/eventos-admin";

// ============================================================
// Tipos e estado inicial
// ============================================================

interface FormularioEvento {
  turma_id: string;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  modo_aplicacao: ModoAplicacaoEvento;
  hora_inicio: string;
  hora_fim: string;
}

const formularioInicial: FormularioEvento = {
  turma_id: "",
  titulo: "",
  data_inicio: "",
  data_fim: "",
  modo_aplicacao: "INFORMATIVO",
  hora_inicio: "",
  hora_fim: "",
};

// ============================================================
// Funções auxiliares
// ============================================================

function formatarData(data: string): string {
  const partes = data.split("-");

  if (partes.length !== 3) {
    return data;
  }

  return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

function prepararDadosEvento(
  formulario: FormularioEvento,
): DadosEvento {
  const turmaId = Number(formulario.turma_id);
  const titulo = formulario.titulo.trim();

  if (!Number.isSafeInteger(turmaId) || turmaId <= 0) {
    throw new Error("Selecione uma turma válida.");
  }

  if (!titulo || titulo.length > 200) {
    throw new Error(
      "Informe um título de até 200 caracteres.",
    );
  }

  if (
    !formulario.data_inicio ||
    !formulario.data_fim
  ) {
    throw new Error(
      "Informe as datas de início e término.",
    );
  }

  if (
    formulario.data_fim < formulario.data_inicio
  ) {
    throw new Error(
      "A data final não pode ser anterior à inicial.",
    );
  }

  const horaInicio = formulario.hora_inicio.trim();
  const horaFim = formulario.hora_fim.trim();

  const possuiInicio = horaInicio !== "";
  const possuiFim = horaFim !== "";

  if (possuiInicio !== possuiFim) {
    throw new Error(
      "Informe os dois horários ou deixe ambos vazios.",
    );
  }

  if (possuiInicio && horaFim <= horaInicio) {
    throw new Error(
      "O horário final deve ser posterior ao inicial.",
    );
  }

  if (
    formulario.modo_aplicacao ===
    "SUBSTITUICAO_PARCIAL"
  ) {
    if (!possuiInicio || !possuiFim) {
      throw new Error(
        "A substituição parcial exige horários de início e término.",
      );
    }

    if (
      formulario.data_inicio !==
      formulario.data_fim
    ) {
      throw new Error(
        "A substituição parcial deve ocorrer em uma única data.",
      );
    }
  }

  return {
    turma_id: turmaId,
    titulo,
    data_inicio: formulario.data_inicio,
    data_fim: formulario.data_fim,
    modo_aplicacao: formulario.modo_aplicacao,
    hora_inicio: possuiInicio ? horaInicio : null,
    hora_fim: possuiFim ? horaFim : null,
  };
}

// ============================================================
// Página administrativa
// ============================================================

export default function EventosAdminPage() {
  const sessao = useAdminSession();
  const { replace } = useRouter();

  // Dados administrativos
  const [anos, setAnos] = useState<AnoLetivo[]>([]);
  const [turmas, setTurmas] = useState<TurmaAdmin[]>([]);
  const [eventos, setEventos] = useState<EventoAdmin[]>([]);

  // Filtros
  const [anoFiltro, setAnoFiltro] = useState("");
  const [turmaFiltro, setTurmaFiltro] = useState("");

  // Formulário
  const [formulario, setFormulario] =
    useState<FormularioEvento>(formularioInicial);

  const [eventoEditando, setEventoEditando] =
    useState<number | null>(null);

  // Estado da página
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [sessaoExpirada, setSessaoExpirada] =
    useState(false);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] =
    useState<string | null>(null);

  // ==========================================================
  // Tratamento de erros HTTP
  // ==========================================================

  const tratarErro = useCallback(
    (falha: unknown) => {
      const classificacao = classificarErroHttp(falha);

      if (classificacao === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        setEventos([]);
        replace("/login");
        return;
      }

      if (classificacao === "ACESSO_NEGADO") {
        setErro(
          "Você não possui permissão para esta operação.",
        );
        return;
      }

      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível realizar a operação.",
      );
    },
    [replace],
  );

  // ==========================================================
  // Carregamento inicial
  // ==========================================================

  useEffect(() => {
    let ativo = true;

    async function carregar() {
      try {
        const [
          anosObtidos,
          turmasObtidas,
          eventosObtidos,
        ] = await Promise.all([
          listarAnosLetivos(),
          listarTurmasAdmin(),
          listarEventosAdmin(),
        ]);

        if (!ativo) return;

        setAnos(anosObtidos);
        setTurmas(turmasObtidas);
        setEventos(eventosObtidos);
      } catch (falha) {
        if (ativo) {
          tratarErro(falha);
        }
      } finally {
        if (ativo) {
          setCarregando(false);
        }
      }
    }

    void carregar();

    return () => {
      ativo = false;
    };
  }, [tratarErro]);

  // ==========================================================
  // Controle do formulário
  // ==========================================================

  function atualizarFormulario(
    campo: keyof FormularioEvento,
    valor: string,
  ) {
    setFormulario((atual) => ({
      ...atual,
      [campo]: valor,
    }));
  }

  function limparFormulario() {
    setFormulario({ ...formularioInicial });
    setEventoEditando(null);
  }

  function editarEvento(evento: EventoAdmin) {
    const turma = turmas.find(
      (item) => item.id === evento.turma_id,
    );

    if (turma) {
      setAnoFiltro(String(turma.ano_letivo_id));
      setTurmaFiltro(String(turma.id));
    }

    setEventoEditando(evento.id);

    setFormulario({
      turma_id: String(evento.turma_id),
      titulo: evento.titulo,
      data_inicio: evento.data_inicio,
      data_fim: evento.data_fim,
      modo_aplicacao:
        evento.modo_aplicacao ?? "INFORMATIVO",
      hora_inicio:
        evento.hora_inicio?.slice(0, 5) ?? "",
      hora_fim:
        evento.hora_fim?.slice(0, 5) ?? "",
    });

    setErro(null);
    setSucesso(null);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  // ==========================================================
  // Criação e atualização
  // ==========================================================

  async function salvarEvento(
    eventoFormulario: FormEvent<HTMLFormElement>,
  ) {
    eventoFormulario.preventDefault();

    if (salvando) return;

    if (!sessao.csrf_token) {
      setErro(
        "Sessão administrativa indisponível. Faça login novamente.",
      );
      return;
    }

    let dados: DadosEvento;

    try {
      dados = prepararDadosEvento(formulario);
    } catch (falha) {
      setErro(
        falha instanceof Error
          ? falha.message
          : "Dados do evento inválidos.",
      );
      return;
    }

    const turmaSelecionada = turmas.find(
      (turma) => turma.id === dados.turma_id,
    );

    if (!turmaSelecionada?.ativo) {
      setErro("Selecione uma turma ativa.");
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      if (eventoEditando === null) {
        const criado = await criarEventoAdmin(
          dados,
          sessao.csrf_token,
        );

        setEventos((atuais) => [
          ...atuais,
          criado,
        ]);

        setSucesso(
          "Evento cadastrado com sucesso.",
        );
      } else {
        const atualizado = await atualizarEventoAdmin(
          eventoEditando,
          dados,
          sessao.csrf_token,
        );

        setEventos((atuais) =>
          atuais.map((item) =>
            item.id === atualizado.id
              ? atualizado
              : item,
          ),
        );

        setSucesso(
          "Evento atualizado com sucesso.",
        );
      }

      limparFormulario();
    } catch (falha) {
      // Inclui conflitos HTTP 409 retornados pelo backend.
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  // ==========================================================
  // Desativação
  // ==========================================================

  async function desativar(evento: EventoAdmin) {
    if (salvando) return;

    const confirmado = window.confirm(
      `Deseja desativar o evento "${evento.titulo}"?`,
    );

    if (!confirmado) return;

    if (!sessao.csrf_token) {
      setErro(
        "Sessão administrativa indisponível.",
      );
      return;
    }

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      await desativarEventoAdmin(
        evento.id,
        sessao.csrf_token,
      );

      setEventos((atuais) =>
        atuais.filter(
          (item) => item.id !== evento.id,
        ),
      );

      if (eventoEditando === evento.id) {
        limparFormulario();
      }

      setSucesso(
        "Evento desativado com sucesso.",
      );
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  // ==========================================================
  // Filtros e identificação
  // ==========================================================

  const turmasDoAno = turmas.filter(
    (turma) =>
      !anoFiltro ||
      turma.ano_letivo_id === Number(anoFiltro),
  );

  const eventosVisiveis = eventos
    .filter((evento) => {
      const turma = turmas.find(
        (item) => item.id === evento.turma_id,
      );

      if (
        anoFiltro &&
        turma?.ano_letivo_id !== Number(anoFiltro)
      ) {
        return false;
      }

      if (
        turmaFiltro &&
        evento.turma_id !== Number(turmaFiltro)
      ) {
        return false;
      }

      return true;
    })
    .sort(
      (a, b) =>
        a.data_inicio.localeCompare(b.data_inicio) ||
        (a.hora_inicio ?? "").localeCompare(
          b.hora_inicio ?? "",
        ) ||
        a.id - b.id,
    );

  function identificarTurma(id: number) {
    const turma = turmas.find(
      (item) => item.id === id,
    );

    return turma?.identificacao ?? `Turma #${id}`;
  }

  if (sessaoExpirada) {
    return (
      <main role="status">
        Sessão expirada. Redirecionando para o login...
      </main>
    );
  }

  // ==========================================================
  // Renderização
  // ==========================================================

  return (
    <main
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "32px",
      }}
    >
      <Link href="/admin">
        Voltar ao painel
      </Link>

      <h1>Gestão de eventos escolares</h1>

      <p>
        Cadastre provas, congressos e atividades
        escolares. Eventos substitutivos poderão
        alterar a programação regular das turmas.
      </p>

      {erro && (
        <p
          role="alert"
          style={{ color: "crimson" }}
        >
          {erro}
        </p>
      )}

      {sucesso && (
        <p
          role="status"
          style={{ color: "green" }}
        >
          {sucesso}
        </p>
      )}

      {carregando ? (
        <p role="status">
          Carregando eventos...
        </p>
      ) : (
        <>
          {/* ====================================== */}
          {/* Filtros */}
          {/* ====================================== */}

          <section style={{ marginTop: "24px" }}>
            <h2>Filtrar eventos</h2>

            <div
              style={{
                display: "flex",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div>
                <label htmlFor="ano-eventos">
                  Ano letivo
                </label>

                <select
                  id="ano-eventos"
                  value={anoFiltro}
                  onChange={(event) => {
                    setAnoFiltro(event.target.value);
                    setTurmaFiltro("");

                    if (eventoEditando === null) {
                      atualizarFormulario(
                        "turma_id",
                        "",
                      );
                    }
                  }}
                >
                  <option value="">
                    Todos os anos
                  </option>

                  {anos.map((ano) => (
                    <option
                      key={ano.id}
                      value={ano.id}
                    >
                      {ano.ano}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="turma-eventos">
                  Turma
                </label>

                <select
                  id="turma-eventos"
                  value={turmaFiltro}
                  onChange={(event) =>
                    setTurmaFiltro(
                      event.target.value,
                    )
                  }
                >
                  <option value="">
                    Todas as turmas
                  </option>

                  {turmasDoAno.map((turma) => (
                    <option
                      key={turma.id}
                      value={turma.id}
                    >
                      {turma.identificacao}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          {/* ====================================== */}
          {/* Formulário */}
          {/* ====================================== */}

          <section style={{ marginTop: "32px" }}>
            <h2>
              {eventoEditando === null
                ? "Cadastrar evento"
                : `Editar evento #${eventoEditando}`}
            </h2>

            <form
              onSubmit={(event) =>
                void salvarEvento(event)
              }
              style={{
                display: "grid",
                gap: "16px",
                maxWidth: "650px",
              }}
            >
              <div>
                <label htmlFor="turma-formulario-evento">
                  Turma
                </label>

                <select
                  id="turma-formulario-evento"
                  required
                  disabled={salvando}
                  value={formulario.turma_id}
                  onChange={(event) =>
                    atualizarFormulario(
                      "turma_id",
                      event.target.value,
                    )
                  }
                >
                  <option value="">
                    Selecione a turma
                  </option>

                  {turmasDoAno
                    .filter(
                      (turma) => turma.ativo,
                    )
                    .map((turma) => (
                      <option
                        key={turma.id}
                        value={turma.id}
                      >
                        {turma.identificacao}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label htmlFor="titulo-evento">
                  Título do evento
                </label>

                <input
                  id="titulo-evento"
                  type="text"
                  required
                  maxLength={200}
                  disabled={salvando}
                  value={formulario.titulo}
                  onChange={(event) =>
                    atualizarFormulario(
                      "titulo",
                      event.target.value,
                    )
                  }
                  placeholder="Ex.: Prova de Matemática"
                />
              </div>

              <div>
                <label htmlFor="inicio-evento">
                  Data inicial
                </label>

                <input
                  id="inicio-evento"
                  type="date"
                  required
                  disabled={salvando}
                  value={formulario.data_inicio}
                  onChange={(event) =>
                    atualizarFormulario(
                      "data_inicio",
                      event.target.value,
                    )
                  }
                />
              </div>

              <div>
                <label htmlFor="fim-evento">
                  Data final
                </label>

                <input
                  id="fim-evento"
                  type="date"
                  required
                  disabled={salvando}
                  min={formulario.data_inicio || undefined}
                  value={formulario.data_fim}
                  onChange={(event) =>
                    atualizarFormulario(
                      "data_fim",
                      event.target.value,
                    )
                  }
                />
              </div>

              {/* Modalidade */}

              <div>
                <label htmlFor="modo-aplicacao">
                  Modalidade do evento
                </label>

                <select
                  id="modo-aplicacao"
                  disabled={salvando}
                  value={formulario.modo_aplicacao}
                  onChange={(event) =>
                    atualizarFormulario(
                      "modo_aplicacao",
                      event.target.value,
                    )
                  }
                >
                  <option value="INFORMATIVO">
                    Informativo — não substitui aulas
                  </option>

                  <option value="SUBSTITUICAO_PARCIAL">
                    Substituição parcial — prova ou atividade
                  </option>

                  <option value="SUBSTITUICAO_INTEGRAL">
                    Substituição integral — programação do dia
                  </option>
                </select>
              </div>

              {/* Horários */}

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "16px",
                }}
              >
                <div>
                  <label htmlFor="hora-inicio">
                    Horário de início
                  </label>

                  <input
                    id="hora-inicio"
                    type="time"
                    disabled={salvando}
                    required={
                      formulario.modo_aplicacao ===
                      "SUBSTITUICAO_PARCIAL"
                    }
                    value={formulario.hora_inicio}
                    onChange={(event) =>
                      atualizarFormulario(
                        "hora_inicio",
                        event.target.value,
                      )
                    }
                  />
                </div>

                <div>
                  <label htmlFor="hora-fim">
                    Horário de término
                  </label>

                  <input
                    id="hora-fim"
                    type="time"
                    disabled={salvando}
                    required={
                      formulario.modo_aplicacao ===
                      "SUBSTITUICAO_PARCIAL"
                    }
                    value={formulario.hora_fim}
                    onChange={(event) =>
                      atualizarFormulario(
                        "hora_fim",
                        event.target.value,
                      )
                    }
                  />
                </div>
              </div>

              {/* Explicação da modalidade */}

              {formulario.modo_aplicacao ===
                "INFORMATIVO" && (
                <p>
                  O evento será exibido na agenda,
                  sem substituir as aulas regulares.
                  Os horários são opcionais.
                </p>
              )}

              {formulario.modo_aplicacao ===
                "SUBSTITUICAO_PARCIAL" && (
                <p>
                  As aulas que coincidirem com o
                  intervalo informado serão
                  substituídas pelo evento. Essa
                  modalidade exige uma única data
                  e os dois horários.
                </p>
              )}

              {formulario.modo_aplicacao ===
                "SUBSTITUICAO_INTEGRAL" && (
                <p>
                  A programação regular das datas
                  selecionadas será substituída
                  integralmente. Os horários são
                  opcionais e indicam a duração
                  da atividade.
                </p>
              )}

              {/* Ações */}

              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  flexWrap: "wrap",
                  marginTop: "8px",
                }}
              >
                <button
                  type="submit"
                  disabled={
                    salvando ||
                    !sessao.csrf_token
                  }
                >
                  {salvando
                    ? "Salvando..."
                    : eventoEditando === null
                      ? "Cadastrar evento"
                      : "Salvar alterações"}
                </button>

                {eventoEditando !== null && (
                  <button
                    type="button"
                    disabled={salvando}
                    onClick={limparFormulario}
                  >
                    Cancelar edição
                  </button>
                )}
              </div>
            </form>
          </section>

          {/* ====================================== */}
          {/* Listagem */}
          {/* ====================================== */}

          <section style={{ marginTop: "36px" }}>
            <h2>Eventos cadastrados</h2>

            {eventosVisiveis.length === 0 ? (
              <p>Nenhum evento encontrado.</p>
            ) : (
              <div
                style={{
                  overflowX: "auto",
                }}
              >
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                  }}
                >
                  <thead>
                    <tr>
                      <th scope="col">Evento</th>
                      <th scope="col">Turma</th>
                      <th scope="col">Início</th>
                      <th scope="col">Fim</th>
                      <th scope="col">Modalidade</th>
                      <th scope="col">Horário</th>
                      <th scope="col">Ações</th>
                    </tr>
                  </thead>

                  <tbody>
                    {eventosVisiveis.map(
                      (evento) => (
                        <tr key={evento.id}>
                          <td>
                            {evento.titulo}
                          </td>

                          <td>
                            {identificarTurma(
                              evento.turma_id,
                            )}
                          </td>

                          <td>
                            {formatarData(
                              evento.data_inicio,
                            )}
                          </td>

                          <td>
                            {formatarData(
                              evento.data_fim,
                            )}
                          </td>

                          <td>
                            {obterDescricaoModoEvento(
                              evento.modo_aplicacao,
                            )}
                          </td>

                          <td>
                            {formatarHorarioEvento(
                              evento.hora_inicio,
                              evento.hora_fim,
                            )}
                          </td>

                          <td>
                            <button
                              type="button"
                              disabled={salvando}
                              onClick={() =>
                                editarEvento(
                                  evento,
                                )
                              }
                            >
                              Editar
                            </button>

                            {" "}

                            <button
                              type="button"
                              disabled={salvando}
                              onClick={() =>
                                void desativar(
                                  evento,
                                )
                              }
                            >
                              Desativar
                            </button>
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
