
from datetime import date, time

import pytest

from app.services.agenda_efetiva import (
    AgendaEfetiva,
    AtividadeEfetiva,
)
from app.services.horarios_liberacao import (
    HorarioLiberacaoInvalido,
    horarios_disponiveis_liberacao,
    validar_horario_liberacao,
)


DATA = date(2026, 10, 28)


@pytest.fixture
def agenda():
    return AgendaEfetiva(
        data=DATA,
        atividades=(
            AtividadeEfetiva(
                hora_inicio=time(13, 10),
                hora_fim=time(14, 50),
                descricao="Literatura",
                tipo="AULA",
                origem="GRADE",
            ),
            AtividadeEfetiva(
                hora_inicio=time(14, 50),
                hora_fim=time(15, 40),
                descricao="Prova de Matemática",
                tipo="EVENTO",
                origem="EVENTO",
                evento_id=10,
            ),
            AtividadeEfetiva(
                hora_inicio=time(15, 40),
                hora_fim=time(16, 10),
                descricao="Intervalo",
                tipo="INTERVALO",
                origem="GRADE",
            ),
            AtividadeEfetiva(
                hora_inicio=time(16, 10),
                hora_fim=time(17, 0),
                descricao="Filosofia",
                tipo="AULA",
                origem="GRADE",
            ),
        ),
        informativos=(),
    )


def test_oferece_aulas_e_provas_mas_nao_intervalos(agenda):
    assert horarios_disponiveis_liberacao(agenda) == (
        time(13, 10),
        time(14, 50),
        time(16, 10),
    )


def test_aceita_inicio_de_prova_na_data_atual(agenda):
    validar_horario_liberacao(
        data_solicitada=DATA,
        data_escolar_atual=DATA,
        horario_solicitado=time(14, 50),
        agenda=agenda,
    )


def test_rejeita_horario_no_meio_da_atividade(agenda):
    with pytest.raises(HorarioLiberacaoInvalido):
        validar_horario_liberacao(
            data_solicitada=DATA,
            data_escolar_atual=DATA,
            horario_solicitado=time(15, 0),
            agenda=agenda,
        )


def test_rejeita_liberacao_em_outra_data(agenda):
    with pytest.raises(
        HorarioLiberacaoInvalido,
        match="data atual",
    ):
        validar_horario_liberacao(
            data_solicitada=DATA,
            data_escolar_atual=date(2026, 10, 29),
            horario_solicitado=time(14, 50),
            agenda=agenda,
        )
