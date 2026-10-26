
"""Construção da agenda efetiva de uma turma.

Este módulo não acessa o banco de dados.
A consulta SQLAlchemy será integrada na E9.3-B.
"""

from dataclasses import dataclass
from datetime import date, time
from typing import Literal


TipoAtividade = Literal[
    "AULA",
    "INTERVALO",
    "EVENTO",
]

ModoEvento = Literal[
    "INFORMATIVO",
    "SUBSTITUICAO_PARCIAL",
    "SUBSTITUICAO_INTEGRAL",
]


@dataclass(frozen=True)
class AulaDaGrade:
    dia_semana: int
    hora_inicio: time
    descricao: str
    tipo: str


@dataclass(frozen=True)
class EventoDoDia:
    id: int
    titulo: str
    data_inicio: date
    data_fim: date
    modo_aplicacao: ModoEvento
    hora_inicio: time | None
    hora_fim: time | None


@dataclass(frozen=True)
class AtividadeEfetiva:
    hora_inicio: time
    hora_fim: time
    descricao: str
    tipo: TipoAtividade
    origem: Literal["GRADE", "EVENTO"]
    evento_id: int | None = None


@dataclass(frozen=True)
class AgendaEfetiva:
    data: date
    atividades: tuple[AtividadeEfetiva, ...]
    informativos: tuple[EventoDoDia, ...]


def construir_agenda_efetiva(
    *,
    data: date,
    horarios: list[time],
    hora_termino: time,
    aulas: list[AulaDaGrade],
    eventos: list[EventoDoDia],
) -> AgendaEfetiva:
    """Combina grade recorrente e eventos da data.

    Os intervalos são semiabertos: [início, fim).
    Substituições parciais podem dividir uma aula.
    """

    if not horarios:
        raise ValueError("A grade não possui horários.")

    limites_grade = sorted(set(horarios))

    if len(limites_grade) != len(horarios):
        raise ValueError("Existem horários repetidos.")

    if hora_termino <= limites_grade[-1]:
        raise ValueError(
            "O término da grade deve ser posterior "
            "ao início do último período."
        )

    limites_grade.append(hora_termino)

    dia_semana = data.weekday()

    aulas_dia = {
        aula.hora_inicio: aula
        for aula in aulas
        if aula.dia_semana == dia_semana
    }

    if len(aulas_dia) != sum(
        1 for aula in aulas if aula.dia_semana == dia_semana
    ):
        raise ValueError(
            "Há atividades duplicadas no mesmo horário."
        )

    if any(
        horario not in limites_grade[:-1]
        for horario in aulas_dia
    ):
        raise ValueError(
            "Há aulas fora dos horários da grade."
        )

    eventos_dia = [
        evento
        for evento in eventos
        if evento.data_inicio <= data <= evento.data_fim
    ]

    informativos = tuple(
        evento
        for evento in eventos_dia
        if evento.modo_aplicacao == "INFORMATIVO"
    )

    substitutivos = [
        evento
        for evento in eventos_dia
        if evento.modo_aplicacao != "INFORMATIVO"
    ]

    integrais = [
        evento
        for evento in substitutivos
        if evento.modo_aplicacao == "SUBSTITUICAO_INTEGRAL"
    ]

    if integrais:
        if len(substitutivos) != 1:
            raise ValueError(
                "Existem eventos substitutivos conflitantes."
            )

        evento = integrais[0]

        inicio = evento.hora_inicio or limites_grade[0]
        fim = evento.hora_fim or hora_termino

        if fim <= inicio:
            raise ValueError("Intervalo do evento inválido.")

        return AgendaEfetiva(
            data=data,
            atividades=(
                AtividadeEfetiva(
                    hora_inicio=inicio,
                    hora_fim=fim,
                    descricao=evento.titulo,
                    tipo="EVENTO",
                    origem="EVENTO",
                    evento_id=evento.id,
                ),
            ),
            informativos=informativos,
        )

    parciais = sorted(
        substitutivos,
        key=lambda evento: (
            evento.hora_inicio or time.min,
            evento.id,
        ),
    )

    for evento in parciais:
        if (
            evento.hora_inicio is None
            or evento.hora_fim is None
            or evento.hora_fim <= evento.hora_inicio
        ):
            raise ValueError(
                "Substituição parcial com horários inválidos."
            )

        if evento.data_inicio != evento.data_fim:
            raise ValueError(
                "Substituição parcial deve ter uma única data."
            )

    for anterior, seguinte in zip(
        parciais,
        parciais[1:],
    ):
        if anterior.hora_fim > seguinte.hora_inicio:
            raise ValueError(
                "Existem eventos substitutivos sobrepostos."
            )

    # Divide os períodos regulares nos pontos em que
    # começam ou terminam os eventos especiais.
    pontos = set(limites_grade)

    for evento in parciais:
        pontos.add(evento.hora_inicio)
        pontos.add(evento.hora_fim)

    pontos_ordenados = sorted(pontos)

    atividades: list[AtividadeEfetiva] = []

    for inicio, fim in zip(
        pontos_ordenados,
        pontos_ordenados[1:],
    ):
        if inicio >= fim:
            continue

        # Prioridade: evento substitutivo.
        evento_ativo = next(
            (
                evento
                for evento in parciais
                if evento.hora_inicio <= inicio
                and fim <= evento.hora_fim
            ),
            None,
        )

        if evento_ativo is not None:
            atividades.append(
                AtividadeEfetiva(
                    hora_inicio=inicio,
                    hora_fim=fim,
                    descricao=evento_ativo.titulo,
                    tipo="EVENTO",
                    origem="EVENTO",
                    evento_id=evento_ativo.id,
                )
            )
            continue

        # Consulta a atividade regular correspondente.
        # Períodos vazios (---) não geram atividade.
        if inicio < limites_grade[0] or inicio >= hora_termino:
            continue

        horario_regular = max(
            horario
            for horario in limites_grade[:-1]
            if horario <= inicio
        )

        aula = aulas_dia.get(horario_regular)

        if aula is None:
            continue

        atividades.append(
            AtividadeEfetiva(
                hora_inicio=inicio,
                hora_fim=fim,
                descricao=aula.descricao,
                tipo=(
                    "INTERVALO"
                    if aula.tipo == "INTERVALO"
                    else "AULA"
                ),
                origem="GRADE",
            )
        )

    # Junta trechos consecutivos da mesma atividade.
    consolidadas: list[AtividadeEfetiva] = []

    for atividade in atividades:
        if consolidadas:
            ultima = consolidadas[-1]

            if (
                ultima.hora_fim == atividade.hora_inicio
                and ultima.descricao == atividade.descricao
                and ultima.tipo == atividade.tipo
                and ultima.origem == atividade.origem
                and ultima.evento_id == atividade.evento_id
            ):
                consolidadas[-1] = AtividadeEfetiva(
                    hora_inicio=ultima.hora_inicio,
                    hora_fim=atividade.hora_fim,
                    descricao=ultima.descricao,
                    tipo=ultima.tipo,
                    origem=ultima.origem,
                    evento_id=ultima.evento_id,
                )
                continue

        consolidadas.append(atividade)

    return AgendaEfetiva(
        data=data,
        atividades=tuple(consolidadas),
        informativos=informativos,
    )
