from __future__ import annotations

from typing import Any


class MotorEventos:
    def __init__(self) -> None:
        self.eventos: list[dict[str, Any]] = []
        self._proximo_id = 1

    def registrar_evento(
        self,
        atualizacao: int,
        tempo_missao: int,
        severidade: str,
        sistema: str,
        mensagem: str,
        diagnostico: str,
        acao_recomendada: str,
    ) -> dict[str, Any]:
        evento = {
            "id": self._proximo_id,
            "atualizacao": atualizacao,
            "tempo_missao": tempo_missao,
            "severidade": severidade,
            "sistema": sistema,
            "mensagem": mensagem,
            "diagnostico": diagnostico,
            "acao_recomendada": acao_recomendada,
            "reconhecido": False,
        }
        self._proximo_id += 1
        self.eventos.append(evento)
        return evento

    def registrar_info(self, atualizacao: int, tempo_missao: int, mensagem: str) -> dict[str, Any]:
        return self.registrar_evento(atualizacao, tempo_missao, "INFO", "Missao", mensagem, "Evento operacional.", "Continuar o monitoramento.")

    def filtrar(self, severidade: str = "todos") -> list[dict[str, Any]]:
        if severidade.lower() == "todos":
            return list(self.eventos)
        return [evento for evento in self.eventos if evento["severidade"] == severidade.upper()]

    def reconhecer_evento(self, evento_id: int) -> None:
        for evento in self.eventos:
            if evento["id"] == evento_id:
                evento["reconhecido"] = True
                return

    def reconhecer_todos(self) -> None:
        for evento in self.eventos:
            evento["reconhecido"] = True


def gerar_eventos_por_estado(
    motor: MotorEventos,
    atualizacao: int,
    tempo_missao: int,
    risco: dict[str, Any],
    energia: dict[str, Any],
) -> list[dict[str, Any]]:
    novos: list[dict[str, Any]] = []
    for chave, analise in risco["analises"].items():
        status, _pontos, mensagem = analise
        if status in {"CRITICO", "ATENCAO"}:
            severidade = "CRITICO" if status == "CRITICO" else "ATENCAO"
            novos.append(
                motor.registrar_evento(
                    atualizacao,
                    tempo_missao,
                    severidade,
                    chave,
                    mensagem,
                    "Parametro fora da faixa nominal.",
                    "Executar a recomendação operacional do sistema.",
                )
            )
    if energia["status"] == "CRITICO":
        novos.append(
            motor.registrar_evento(
                atualizacao,
                tempo_missao,
                "CRITICO",
                "Sistema de energia",
                "Energia em emergencia",
                "Bateria crítica com saldo energético negativo.",
                "Reduzir as cargas não essenciais.",
            )
        )
    return novos
