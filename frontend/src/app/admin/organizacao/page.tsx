
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
  listarAlunosAdmin,
  type AlunoAdmin,
} from "@/lib/alunos-admin";


import {
  listarAnosLetivos,
  criarAnoLetivo,
  atualizarAnoLetivo,
  type AnoLetivo,
} from "@/lib/anos-letivos-admin";

import {
  listarTurmasAdmin,
  criarTurmaAdmin,
  alterarSituacaoTurma,
  type TurmaAdmin,
} from "@/lib/turmas-admin";

import {
  listarMatriculas,
  criarMatricula,
  encerrarMatricula,
  transferirMatricula,
  type MatriculaAdmin,
} from "@/lib/matriculas-admin";


export default function OrganizacaoEscolarPage() {
  const { csrf_token } = useAdminSession();
  const { replace } = useRouter();

  const [anos, setAnos] = useState<AnoLetivo[]>([]);
  const [turmas, setTurmas] = useState<TurmaAdmin[]>([]);
  const [alunos, setAlunos] = useState<AlunoAdmin[]>([]);
  const [matriculas, setMatriculas] =
    useState<MatriculaAdmin[]>([]);

  const [anoNovo, setAnoNovo] = useState(
    String(new Date().getFullYear()),
  );
  const [anoSelecionado, setAnoSelecionado] = useState("");

  const [identificacao, setIdentificacao] = useState("");
  const [anoEscolar, setAnoEscolar] = useState("1");
  const [turno, setTurno] = useState("MANHA");

  const [alunoId, setAlunoId] = useState("");
  const [turmaId, setTurmaId] = useState("");
  const [dataInicio, setDataInicio] = useState("");

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [sessaoExpirada, setSessaoExpirada] =
    useState(false);

  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);

  const tratarErro = useCallback(
    (falha: unknown) => {
      const tipo = classificarErroHttp(falha);

      if (tipo === "NAO_AUTENTICADO") {
        setSessaoExpirada(true);
        replace("/login");
        return;
      }

      setErro(
        tipo === "ACESSO_NEGADO"
          ? "Acesso administrativo negado."
          : falha instanceof Error
            ? falha.message
            : "Não foi possível concluir a operação.",
      );
    },
    [replace],
  );

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);

    try {
      const [
        anosObtidos,
        turmasObtidas,
        alunosObtidos,
        matriculasObtidas,
      ] = await Promise.all([
        listarAnosLetivos(),
        listarTurmasAdmin(),
        listarAlunosAdmin(),
        listarMatriculas(),
      ]);

      setAnos(anosObtidos);
      setTurmas(turmasObtidas);
      setAlunos(alunosObtidos);
      setMatriculas(matriculasObtidas);
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setCarregando(false);
    }
  }, [tratarErro]);

  useEffect(() => {
    let ativo = true;

    async function iniciar() {
      try {
        const [a, t, al, m] = await Promise.all([
          listarAnosLetivos(),
          listarTurmasAdmin(),
          listarAlunosAdmin(),
          listarMatriculas(),
        ]);

        if (!ativo) return;

        setAnos(a);
        setTurmas(t);
        setAlunos(al);
        setMatriculas(m);
      } catch (falha) {
        if (ativo) tratarErro(falha);
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    void iniciar();

    return () => {
      ativo = false;
    };
  }, [tratarErro]);

  async function executar(
    operacao: () => Promise<void>,
  ) {
    if (salvando) return;

    setSalvando(true);
    setErro(null);
    setSucesso(null);

    try {
      await operacao();
    } catch (falha) {
      tratarErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  function cadastrarAno(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    void executar(async () => {
      const novo = await criarAnoLetivo(
        Number(anoNovo),
        csrf_token,
      );

      setAnos((atuais) =>
        [...atuais, novo].sort((a, b) => a.ano - b.ano),
      );

      setAnoSelecionado(String(novo.id));
      setSucesso("Ano letivo cadastrado.");
    });
  }

  function cadastrarTurma(
    evento: FormEvent<HTMLFormElement>,
  ) {
    evento.preventDefault();

    if (!anoSelecionado) return;

    void executar(async () => {
      const nova = await criarTurmaAdmin(
        {
          identificacao: identificacao.trim(),
          ano_escolar: Number(anoEscolar),
          ano_letivo_id: Number(anoSelecionado),
          turno,
        },
        csrf_token,
      );

      setTurmas((atuais) => [...atuais, nova]);
      setIdentificacao("");
      setSucesso("Turma cadastrada.");
    });
  }

  function cadastrarMatricula(
    evento: FormEvent<HTMLFormElement>,
  ) {
    evento.preventDefault();

    if (!alunoId || !turmaId || !dataInicio) return;

    void executar(async () => {
      const nova = await criarMatricula(
        {
          aluno_id: Number(alunoId),
          turma_id: Number(turmaId),
          ano_letivo_id: Number(anoSelecionado),
          data_inicio: dataInicio,
          data_fim: null,
        },
        csrf_token,
      );

      setMatriculas((atuais) => [...atuais, nova]);
      setAlunoId("");
      setTurmaId("");
      setSucesso("Matrícula registrada.");
    });
  }

  const anoAtual = anos.find(
    (ano) => ano.id === Number(anoSelecionado),
  );

  const turmasDoAno = turmas.filter(
    (turma) =>
      turma.ano_letivo_id === Number(anoSelecionado),
  );

  const matriculasDoAno = matriculas.filter(
    (matricula) =>
      matricula.ano_letivo_id ===
      Number(anoSelecionado),
  );

  function nomeAluno(id: number) {
    return alunos.find((aluno) => aluno.id === id)
      ?.nome_completo ?? `Aluno #${id}`;
  }

  function nomeTurma(id: number) {
    return turmas.find((turma) => turma.id === id)
      ?.identificacao ?? `Turma #${id}`;
  }

  
  function alternarAno(ano: AnoLetivo) {
  if (
    !window.confirm(
      `Deseja ${ano.ativo ? "desativar" : "ativar"} o ano letivo ${ano.ano}?`,
    )
  ) {
    return;
  }

  void executar(async () => {
    const atualizado = await atualizarAnoLetivo(
      ano.id,
      !ano.ativo,
      csrf_token,
    );

    setAnos((atuais) =>
      atuais.map((item) =>
        item.id === atualizado.id ? atualizado : item,
      ),
    );

    setSucesso("Situação do ano letivo atualizada.");
  });
  }
  
  function alternarTurma(turma: TurmaAdmin) {
  if (
    !window.confirm(
      `Deseja ${turma.ativo ? "desativar" : "ativar"} a turma ${turma.identificacao}?`,
    )
  ) {
    return;
  }

  void executar(async () => {
    const atualizada = await alterarSituacaoTurma(
      turma.id,
      !turma.ativo,
      csrf_token,
    );

    setTurmas((atuais) =>
      atuais.map((item) =>
        item.id === atualizada.id ? atualizada : item,
      ),
    );

    setSucesso("Situação da turma atualizada.");
  });
  }
  
  function encerrar(matricula: MatriculaAdmin) {
  if (matricula.data_fim !== null) return;

  const dataFim = window.prompt(
    "Informe a data de encerramento (AAAA-MM-DD):",
    new Date().toLocaleDateString("en-CA"),
  );

  if (dataFim === null) return;

  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(dataFim) ||
    dataFim < matricula.data_inicio
  ) {
    setErro("Informe uma data de encerramento válida.");
    return;
  }

  void executar(async () => {
    const atualizada = await encerrarMatricula(
      matricula.id,
      dataFim,
      csrf_token,
    );

    setMatriculas((atuais) =>
      atuais.map((item) =>
        item.id === atualizada.id ? atualizada : item,
      ),
    );

    setSucesso("Matrícula encerrada.");
  });
  }
  
  function transferir(matricula: MatriculaAdmin) {
  if (matricula.data_fim !== null) return;

  const destinos = turmas.filter(
    (turma) =>
      turma.ativo &&
      turma.ano_letivo_id === matricula.ano_letivo_id &&
      turma.id !== matricula.turma_id,
  );

  if (destinos.length === 0) {
    setErro("Não existem turmas disponíveis para transferência.");
    return;
  }

  const opcoes = destinos
    .map((turma) => `${turma.id} - ${turma.identificacao}`)
    .join("\n");

  const destinoInformado = window.prompt(
    `Informe o ID da turma de destino:\n${opcoes}`,
  );

  if (destinoInformado === null) return;

  const destinoId = Number(destinoInformado);

  if (
    !Number.isSafeInteger(destinoId) ||
    !destinos.some((turma) => turma.id === destinoId)
  ) {
    setErro("Turma de destino inválida.");
    return;
  }

  const dataTransferencia = window.prompt(
    "Informe a data da transferência (AAAA-MM-DD):",
    new Date().toLocaleDateString("en-CA"),
  );

  if (dataTransferencia === null) return;

  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(dataTransferencia) ||
    dataTransferencia <= matricula.data_inicio
  ) {
    setErro(
      "A transferência deve ocorrer depois da data inicial da matrícula.",
    );
    return;
  }

  void executar(async () => {
    const resultado = await transferirMatricula(
      matricula.id,
      destinoId,
      dataTransferencia,
      csrf_token,
    );

    setMatriculas((atuais) => [
      ...atuais.map((item) =>
        item.id === resultado.matricula_anterior.id
          ? resultado.matricula_anterior
          : item,
      ),
      resultado.nova_matricula,
    ]);

    setSucesso("Transferência realizada com sucesso.");
  });
  }

  if (sessaoExpirada) {
    return (
      <main role="status">
        Sessão expirada. Redirecionando para o login...
      </main>
    );
  }

  return (
    <main
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "32px",
      }}
    >
      <Link href="/admin">Voltar ao painel</Link>

      <h1>Organização escolar</h1>
      <p>Gerencie anos letivos, turmas e matrículas.</p>
      <Link href="/admin/organizacao/horarios">
        Gerenciar grades horárias
      </Link>

      {erro && <p role="alert">{erro}</p>}
      {sucesso && <p role="status">{sucesso}</p>}

      <button
        type="button"
        onClick={() => void carregar()}
        disabled={carregando || salvando}
      >
        Atualizar dados
      </button>

      {carregando ? (
        <p role="status">Carregando organização...</p>
      ) : (
        <>
          <section style={{ marginTop: "32px" }}>
            <h2>Anos letivos</h2>
            {anoAtual && (
                <p>
                    Situação: {anoAtual.ativo ? "Ativo" : "Inativo"}{" "}
                    <button
                    type="button"
                    disabled={salvando}
                    onClick={() => alternarAno(anoAtual)}
                    >
                    {anoAtual.ativo ? "Desativar ano" : "Ativar ano"}
                    </button>
                </p>
            )}
            <form onSubmit={cadastrarAno}>
              <label htmlFor="novo-ano">Ano</label>
              <input
                id="novo-ano"
                type="number"
                min={1}
                max={9999}
                step={1}
                required
                value={anoNovo}
                onChange={(evento) =>
                  setAnoNovo(evento.target.value)
                }
              />
              <button disabled={salvando} type="submit">
                Cadastrar ano
              </button>
            </form>

            <label htmlFor="ano-selecionado">
              Ano letivo de trabalho
            </label>

            <select
              id="ano-selecionado"
              value={anoSelecionado}
              onChange={(evento) => {
                setAnoSelecionado(evento.target.value);
                setTurmaId("");
              }}
            >
              <option value="">Selecione o ano</option>
              {anos.map((ano) => (
                <option key={ano.id} value={ano.id}>
                  {ano.ano}
                  {!ano.ativo ? " (inativo)" : ""}
                </option>
              ))}
            </select>
          </section>

          {anoAtual && (
            <>
              <section style={{ marginTop: "32px" }}>
                <h2>Turmas de {anoAtual.ano}</h2>

                <form onSubmit={cadastrarTurma}>
                  <label htmlFor="identificacao">
                    Identificação
                  </label>
                  <input
                    id="identificacao"
                    maxLength={50}
                    required
                    value={identificacao}
                    onChange={(evento) =>
                      setIdentificacao(evento.target.value)
                    }
                    placeholder="1º Ano A"
                  />

                  <label htmlFor="ano-escolar">
                    Ano escolar
                  </label>
                  <input
                    id="ano-escolar"
                    type="number"
                    min={1}
                    step={1}
                    required
                    value={anoEscolar}
                    onChange={(evento) =>
                      setAnoEscolar(evento.target.value)
                    }
                  />

                  <label htmlFor="turno">Turno</label>
                  <select
                    id="turno"
                    value={turno}
                    onChange={(evento) =>
                      setTurno(evento.target.value)
                    }
                  >
                    <option value="MANHA">Manhã</option>
                    <option value="NOITE">Noite</option>
                  </select>

                  <button
                    type="submit"
                    disabled={salvando || !anoAtual.ativo}
                  >
                    Cadastrar turma
                  </button>
                </form>

                <ul>
                    {turmasDoAno.map((turma) => (
                        <li key={turma.id}>
                        {turma.identificacao} — {turma.turno}
                        {" — "}
                        {turma.ativo ? "Ativa" : "Inativa"}
                        {" "}
                        <button
                            type="button"
                            disabled={salvando || !anoAtual.ativo}
                            onClick={() => alternarTurma(turma)}
                        >
                            {turma.ativo ? "Desativar" : "Ativar"}
                        </button>
                        </li>
                    ))}
                </ul>
              </section>

              <section style={{ marginTop: "32px" }}>
                <h2>Matricular aluno</h2>

                <form onSubmit={cadastrarMatricula}>
                  <label htmlFor="aluno-matricula">
                    Aluno
                  </label>

                  <select
                    id="aluno-matricula"
                    required
                    value={alunoId}
                    onChange={(evento) =>
                      setAlunoId(evento.target.value)
                    }
                  >
                    <option value="">Selecione</option>
                    {alunos
                      .filter((aluno) => aluno.ativo)
                      .map((aluno) => (
                        <option
                          key={aluno.id}
                          value={aluno.id}
                        >
                          {aluno.nome_completo}
                        </option>
                      ))}
                  </select>

                  <label htmlFor="turma-matricula">
                    Turma
                  </label>

                  <select
                    id="turma-matricula"
                    required
                    value={turmaId}
                    onChange={(evento) =>
                      setTurmaId(evento.target.value)
                    }
                  >
                    <option value="">Selecione</option>
                    {turmasDoAno
                      .filter((turma) => turma.ativo)
                      .map((turma) => (
                        <option
                          key={turma.id}
                          value={turma.id}
                        >
                          {turma.identificacao}
                        </option>
                      ))}
                  </select>

                  <label htmlFor="inicio-matricula">
                    Data de início
                  </label>

                  <input
                    id="inicio-matricula"
                    type="date"
                    required
                    value={dataInicio}
                    onChange={(evento) =>
                      setDataInicio(evento.target.value)
                    }
                  />

                  <button
                    type="submit"
                    disabled={salvando || !anoAtual.ativo}
                  >
                    Registrar matrícula
                  </button>
                </form>
              </section>

              <section style={{ marginTop: "32px" }}>
                <h2>Matrículas de {anoAtual.ano}</h2>

                <table>
                  <thead>
                    <tr>
                      <th scope="col">Aluno</th>
                      <th scope="col">Turma</th>
                      <th scope="col">Ações</th>
                      <th scope="col">Início</th>
                      <th scope="col">Fim</th>
                    </tr>
                  </thead>

                  <tbody>
                    {matriculasDoAno.map((matricula) => (
                      <tr key={matricula.id}>
                        <td>
                          {nomeAluno(matricula.aluno_id)}
                        </td>
                        <td>
                          {nomeTurma(matricula.turma_id)}
                        </td>
                        <td>{matricula.data_inicio}</td>
                        <td>
                          {matricula.data_fim ??
                            "Em aberto"}
                        </td>
                        <td>
                            {matricula.data_fim === null ? (
                                <>
                                <button
                                    type="button"
                                    disabled={salvando}
                                    onClick={() => encerrar(matricula)}
                                >
                                    Encerrar
                                </button>
                                {" "}
                                <button
                                    type="button"
                                    disabled={salvando || !anoAtual.ativo}
                                    onClick={() => transferir(matricula)}
                                >
                                    Transferir
                                </button>
                                </>
                            ) : (
                                <span>Encerrada</span>
                            )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}
