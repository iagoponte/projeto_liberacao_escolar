
import pytest

from app.services.importacao_grade import (
    GradeCSVInvalida,
    importar_grade_csv,
)


CSV_EXEMPLO = """\
Horários,segunda,terça,quarta,quinta,sexta
13:10,gramática,biologia,literatura,inglês,física
14:00,gramática,biologia,literatura,espanhol,física
15:40,intervalo,intervalo,intervalo,intervalo,intervalo
17:50,---,---,oficina de redação,química,---
"""


def test_importa_grade_semanal():
    grade = importar_grade_csv(CSV_EXEMPLO)

    assert len(grade.horarios) == 4
    assert len(grade.aulas) == 17

    quarta = [
        aula
        for aula in grade.aulas
        if aula.dia_semana == 2
    ]

    assert [aula.descricao for aula in quarta] == [
        "literatura",
        "literatura",
        "intervalo",
        "oficina de redação",
    ]

    assert quarta[2].tipo == "INTERVALO"


def test_aceita_csv_com_ponto_e_virgula_e_bom():
    conteudo = (
        "\ufeffHorários;segunda;terça;quarta;quinta;sexta\n"
        "13:10;gramática;biologia;literatura;inglês;física\n"
    )

    grade = importar_grade_csv(conteudo)

    assert len(grade.aulas) == 5


def test_rejeita_horarios_repetidos():
    conteudo = (
        "Horários,segunda,terça,quarta,quinta,sexta\n"
        "13:10,gramática,biologia,literatura,inglês,física\n"
        "13:10,química,história,matemática,inglês,física\n"
    )

    with pytest.raises(
        GradeCSVInvalida,
        match="nao podem se repetir",
    ):
        importar_grade_csv(conteudo)
