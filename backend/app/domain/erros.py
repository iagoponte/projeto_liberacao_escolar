class ErroDominio(Exception):
    """Base das violacoes de regra de negocio."""


class DataNaoPermitida(ErroDominio):
    """A operacao so e permitida para a data atual da escola."""


class ForaDoHorarioLimite(ErroDominio):
    """O responsavel tentou operar apos o horario-limite do turno."""


class VinculoInvalido(ErroDominio):
    """Nao ha vinculo vigente entre o responsavel e o aluno."""


class TransicaoInvalida(ErroDominio):
    """A transicao de estado solicitada nao e permitida."""


class MotivoObrigatorio(ErroDominio):
    """Correcao administrativa exige motivo."""