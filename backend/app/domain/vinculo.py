from dataclasses import dataclass
from datetime import datetime

from app.domain.relogio import exigir_instante_com_fuso


@dataclass(frozen=True)
class Vinculo:
    responsavel_id: int
    aluno_id: int
    vigente_desde: datetime
    revogado_em: datetime | None = None

    def vigente_em(self, instante: datetime) -> bool:
        exigir_instante_com_fuso(instante)
        if instante < self.vigente_desde:
            return False
        return self.revogado_em is None or instante < self.revogado_em