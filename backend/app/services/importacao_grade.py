
"""Interpretação e validação da grade horária semanal em CSV."""

import csv
import io
import unicodedata
from dataclasses import dataclass
from datetime import time


DIAS_SEMANA = (
    "segunda",
    "terca",
    "quarta",
    "quinta",
    "sexta",
)

LIMITE_LINHAS = 100


class GradeCSVInvalida(ValueError):
    pass


@dataclass(frozen=True)
class AulaImportada:
    dia_semana: int  # segunda = 0, sexta = 4
    hora_inicio: time
    descricao: str
    tipo: str  # AULA ou INTERVALO


@dataclass(frozen=True)
class GradeImportada:
    aulas: tuple[AulaImportada, ...]
    horarios: tuple[time, ...]


def normalizar_texto(valor: str) -> str:
    texto = unicodedata.normalize(
        "NFKD",
        valor.strip().lower(),
    )

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )


def interpretar_horario(valor: str) -> time:
    partes = valor.strip().split(":")

    if len(partes) != 2:
        raise GradeCSVInvalida(
            f"Horario invalido: {valor!r}. Use HH:MM."
        )

    horas, minutos = partes

    if (
        len(horas) != 2
        or len(minutos) != 2
        or not horas.isascii()
        or not minutos.isascii()
        or not horas.isdigit()
        or not minutos.isdigit()
    ):
        raise GradeCSVInvalida(
            f"Horario invalido: {valor!r}. Use HH:MM."
        )

    hora = int(horas)
    minuto = int(minutos)

    if hora > 23 or minuto > 59:
        raise GradeCSVInvalida(
            f"Horario fora do intervalo: {valor!r}."
        )

    return time(hour=hora, minute=minuto)


def importar_grade_csv(conteudo: str) -> GradeImportada:
    if not conteudo.strip():
        raise GradeCSVInvalida("O CSV esta vazio.")

    amostra = conteudo.lstrip("\ufeff").splitlines()[0]

    separador = (
        ";" if amostra.count(";") > amostra.count(",")
        else ","
    )

    leitor = csv.reader(
        io.StringIO(conteudo.lstrip("\ufeff")),
        delimiter=separador,
        strict=True,
    )

    try:
        linhas = [
            linha
            for linha in leitor
            if any(celula.strip() for celula in linha)
        ]
    except csv.Error as exc:
        raise GradeCSVInvalida(
            "Estrutura CSV invalida."
        ) from exc

    if len(linhas) < 2:
        raise GradeCSVInvalida(
            "Informe o cabecalho e pelo menos um horario."
        )

    cabecalho = [
        normalizar_texto(celula)
        for celula in linhas[0]
    ]

    esperado = ["horarios", *DIAS_SEMANA]

    if cabecalho != esperado:
        raise GradeCSVInvalida(
            "Cabecalho esperado: "
            "Horarios,segunda,terca,quarta,quinta,sexta."
        )

    if len(linhas) - 1 > LIMITE_LINHAS:
        raise GradeCSVInvalida(
            "CSV excede o limite de horarios."
        )

    aulas: list[AulaImportada] = []
    horarios: list[time] = []

    for numero_linha, linha in enumerate(
        linhas[1:],
        start=2,
    ):
        if len(linha) != 6:
            raise GradeCSVInvalida(
                f"Linha {numero_linha}: "
                "esperadas seis colunas."
            )

        horario = interpretar_horario(linha[0])

        if horarios and horario <= horarios[-1]:
            raise GradeCSVInvalida(
                f"Linha {numero_linha}: "
                "os horarios devem ser crescentes "
                "e nao podem se repetir."
            )

        horarios.append(horario)

        for dia, celula in enumerate(linha[1:]):
            descricao = celula.strip()

            if not descricao or descricao == "---":
                continue

            if len(descricao) > 200:
                raise GradeCSVInvalida(
                    f"Linha {numero_linha}: "
                    "descricao com mais de 200 caracteres."
                )

            tipo = (
                "INTERVALO"
                if normalizar_texto(descricao) == "intervalo"
                else "AULA"
            )

            aulas.append(
                AulaImportada(
                    dia_semana=dia,
                    hora_inicio=horario,
                    descricao=descricao,
                    tipo=tipo,
                )
            )

    if not aulas:
        raise GradeCSVInvalida(
            "O CSV nao contem aulas ou intervalos."
        )

    return GradeImportada(
        aulas=tuple(aulas),
        horarios=tuple(horarios),
    )
