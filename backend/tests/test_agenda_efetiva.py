
from datetime import date, time

from app.services.agenda_efetiva import (
    AulaDaGrade,
    EventoDoDia,
    construir_agenda_efetiva,
)


DATA = date(2026, 10, 28)  # Quarta-feira

HORARIOS = [
    time(13, 10),
    time(14, 0),
    time(14, 50),
    time(15, 40),
    time(16, 10),
    time(17, 0),
    time(17, 50),
]

AULAS = [
    AulaDaGrade(2, time(13, 10), "Literatura", "AULA"),
    AulaDaGrade(2, time(14, 0), "Literatura", "AULA"),
    AulaDaGrade(2, time(14, 50), "Matemática I", "AULA"),
    AulaDaGrade(2, time(15, 40), "Intervalo", "INTERVALO"),
    AulaDaGrade(2, time(16, 10), "Filosofia", "AULA"),
    AulaDaGrade(2, time(17, 0), "Redação", "AULA"),
    AulaDaGrade(
        2, time(17, 50), "Oficina de redação", "AULA"
    ),
]


def criar_agenda(eventos):
    return construir_agenda_efetiva(
        data=DATA,
        horarios=HORARIOS,
        hora_termino=time(18, 40),
        aulas=AULAS,
        eventos=eventos,
    )


def test_prova_substitui_parte_da_programacao():
    prova = EventoDoDia(
        id=10,
        titulo="Prova de Matemática",
        data_inicio=DATA,
        data_fim=DATA,
        modo_aplicacao="SUBSTITUICAO_PARCIAL",
        hora_inicio=time(14, 50),
        hora_fim=time(17, 0),
    )

    agenda = criar_agenda([prova])

    assert any(
        atividade.descricao == "Prova de Matemática"
        and atividade.hora_inicio == time(14, 50)
        and atividade.hora_fim == time(17, 0)
        for atividade in agenda.atividades
    )

    assert any(
        atividade.descricao == "Redação"
        and atividade.hora_inicio == time(17, 0)
        for atividade in agenda.atividades
    )

    assert not any(
        atividade.descricao == "Filosofia"
        for atividade in agenda.atividades
    )


def test_congresso_integral_substitui_grade():
    congresso = EventoDoDia(
        id=20,
        titulo="Congresso Escolar",
        data_inicio=DATA,
        data_fim=DATA,
        modo_aplicacao="SUBSTITUICAO_INTEGRAL",
        hora_inicio=time(13, 10),
        hora_fim=time(18, 0),
    )

    agenda = criar_agenda([congresso])

    assert len(agenda.atividades) == 1
    assert agenda.atividades[0].descricao == "Congresso Escolar"
    assert agenda.atividades[0].hora_fim == time(18, 0)


def test_evento_informativo_nao_substitui_aulas():
    aviso = EventoDoDia(
        id=30,
        titulo="Reunião de responsáveis",
        data_inicio=DATA,
        data_fim=DATA,
        modo_aplicacao="INFORMATIVO",
        hora_inicio=time(15, 0),
        hora_fim=time(16, 0),
    )

    agenda = criar_agenda([aviso])

    assert len(agenda.informativos) == 1
    assert agenda.informativos[0].titulo == (
        "Reunião de responsáveis"
    )

    assert any(
        atividade.descricao == "Matemática I"
        for atividade in agenda.atividades
    )

    assert any(
        atividade.descricao == "Filosofia"
        for atividade in agenda.atividades
    )
