from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .assistente_ia import analisar_missao_com_ia, aquecer_modelo_ollama, gerar_telemetria_ia_com_fallback
from .configuracao_simulacao import ConfiguracaoMissao
from .gerador_telemetria import gerar_telemetria
from .motor_energia import analisar_energia
from .motor_eventos import MotorEventos, gerar_eventos_por_estado
from .motor_risco import calcular_pontuacao_risco, gerar_recomendacoes_operacionais


@dataclass
class EstadoMissao:
    configuracao: ConfiguracaoMissao
    atualizacao_atual: int = 0
    tempo_decorrido_min: int = 0
    fase_missao: str = "PREPARACAO"
    modo_operacional: str = "AGUARDANDO"
    status_geral: str = "NOMINAL"
    historico_telemetria: list[dict[str, Any]] = field(default_factory=list)
    historico_energia: list[dict[str, Any]] = field(default_factory=list)
    historico_risco: list[dict[str, Any]] = field(default_factory=list)
    historico_ia: list[dict[str, Any]] = field(default_factory=list)
    historico_analise_ia: list[dict[str, str]] = field(default_factory=list)
    aquecimento_ia: dict[str, Any] = field(default_factory=dict)
    alertas_ativos: list[dict[str, Any]] = field(default_factory=list)
    historico_eventos: list[dict[str, Any]] = field(default_factory=list)
    ultima_atualizacao: dict[str, Any] | None = None
    missao_em_execucao: bool = False
    missao_pausada: bool = False
    missao_finalizada: bool = False
    motor_eventos: MotorEventos = field(default_factory=MotorEventos)

    @property
    def total_atualizacoes(self) -> int:
        return self.configuracao.total_atualizacoes

    @property
    def tempo_restante_min(self) -> int:
        return max(0, self.configuracao.duracao_minutos - self.tempo_decorrido_min)

    def iniciar_simulacao(self) -> None:
        self.atualizacao_atual = 0
        self.tempo_decorrido_min = 0
        self.fase_missao = "INICIO"
        self.modo_operacional = "MONITORAMENTO"
        self.status_geral = "NOMINAL"
        self.historico_telemetria.clear()
        self.historico_energia.clear()
        self.historico_risco.clear()
        self.historico_ia.clear()
        self.historico_analise_ia.clear()
        self.aquecimento_ia.clear()
        self.alertas_ativos.clear()
        self.ultima_atualizacao = None
        self.motor_eventos = MotorEventos()
        self.historico_eventos = self.motor_eventos.eventos
        self.motor_eventos.registrar_info(0, 0, "Missão iniciada.")
        if self.configuracao.fonte_dados == "ia_regras" and self.configuracao.aquecer_modelo_ao_iniciar:
            self.aquecimento_ia = {"ok": False, "motivo": "Aquecimento pendente.", "modelo": ""}
        self.missao_em_execucao = True
        self.missao_pausada = False
        self.missao_finalizada = False

    def avancar_atualizacao(self) -> dict[str, Any] | None:
        if self.missao_finalizada or self.atualizacao_atual >= self.total_atualizacoes:
            return None
        if not self.missao_em_execucao:
            self.iniciar_simulacao()

        self.atualizacao_atual += 1
        self.tempo_decorrido_min = self.atualizacao_atual * self.configuracao.intervalo_monitoramento_min
        self.atualizar_fase_missao()
        fallback = gerar_telemetria(self.configuracao, self.atualizacao_atual)
        if self.configuracao.fonte_dados == "ia_regras":
            resultado_ia = gerar_telemetria_ia_com_fallback(
                self.configuracao,
                self.atualizacao_atual,
                fallback,
                timeout_s=self.configuracao.timeout_telemetria_ia,
            )
            telemetria = resultado_ia["telemetria"]
        else:
            resultado_ia = {
                "telemetria": fallback,
                "origem": "regras internas",
                "validacao": "IA desativada.",
                "json_bruto": "",
            }
            telemetria = fallback
        risco = calcular_pontuacao_risco(telemetria)
        energia = analisar_energia(telemetria)
        self.historico_telemetria.append(telemetria)
        self.historico_risco.append(risco)
        self.historico_energia.append(energia)
        self.historico_ia.append(resultado_ia)
        self.status_geral = self.classificar_status_geral(risco, energia)
        self.atualizar_modo_operacional()
        self.alertas_ativos = gerar_eventos_por_estado(self.motor_eventos, self.atualizacao_atual, self.tempo_decorrido_min, risco, energia)
        self.ultima_atualizacao = {"telemetria": telemetria, "risco": risco, "energia": energia}

        if self.atualizacao_atual >= self.total_atualizacoes:
            self.finalizar_simulacao()
        return self.ultima_atualizacao

    def executar_ate_o_fim(self) -> None:
        while not self.missao_finalizada:
            self.avancar_atualizacao()

    def executar_automaticamente(self) -> dict[str, Any] | None:
        if self.missao_pausada:
            return None
        return self.avancar_atualizacao()

    def pausar_simulacao(self) -> None:
        self.missao_pausada = True
        self.modo_operacional = "PAUSADA"
        self.motor_eventos.registrar_info(self.atualizacao_atual, self.tempo_decorrido_min, "Missão pausada.")

    def reiniciar_simulacao(self) -> None:
        self.iniciar_simulacao()

    def finalizar_simulacao(self) -> None:
        self.missao_finalizada = True
        self.missao_em_execucao = False
        self.fase_missao = "FINALIZADA"
        self.status_geral = "FINALIZADA" if self.status_geral == "NOMINAL" else self.status_geral
        self.motor_eventos.registrar_info(self.atualizacao_atual, self.tempo_decorrido_min, "Missão finalizada.")

    def calcular_tempo_decorrido(self) -> int:
        return self.tempo_decorrido_min

    def calcular_tempo_restante(self) -> int:
        return self.tempo_restante_min

    def atualizar_fase_missao(self) -> str:
        fase_anterior = self.fase_missao
        self.fase_missao = self._calcular_fase()
        if fase_anterior != self.fase_missao and self.atualizacao_atual > 0:
            self.motor_eventos.registrar_info(
                self.atualizacao_atual,
                self.tempo_decorrido_min,
                f"Fase alterada para {self.fase_missao}.",
            )
        return self.fase_missao

    def atualizar_modo_operacional(self) -> str:
        if self.missao_pausada:
            self.modo_operacional = "PAUSADA"
        elif self.missao_finalizada:
            self.modo_operacional = "FINALIZADA"
        elif self.historico_energia:
            self.modo_operacional = self.historico_energia[-1]["modo_energetico"]
        else:
            self.modo_operacional = "MONITORAMENTO"
        return self.modo_operacional

    def classificar_status_geral(self, risco: dict[str, Any], energia: dict[str, Any]) -> str:
        criticos_ativos = sum(1 for evento in self.alertas_ativos if evento["severidade"] == "CRITICO")
        tendencia = self.tendencia_risco()
        if energia["status"] == "CRITICO" and risco["pontuacao"] >= 6:
            return "CONTINGENCIA"
        if risco["pontuacao"] >= 9 or criticos_ativos >= 3:
            return "CONTINGENCIA"
        if risco["pontuacao"] >= 6 or energia["status"] == "CRITICO":
            return "CRITICO"
        if risco["pontuacao"] >= 3 or tendencia == "piorando" or energia["status"] == "ATENCAO":
            return "ATENCAO"
        return "NOMINAL"

    def tendencia_risco(self) -> str:
        if len(self.historico_risco) < 3:
            return "estavel"
        ultimos = [item["pontuacao"] for item in self.historico_risco[-3:]]
        if ultimos[-1] > ultimos[0]:
            return "piorando"
        if ultimos[-1] < ultimos[0]:
            return "melhorando"
        return "estavel"

    def analise_comunicacao_atual(self) -> dict[str, Any]:
        if not self.historico_telemetria:
            return {
                "status": "SEM DADOS",
                "qualidade": 0,
                "latencia": 0,
                "perda": 0,
                "ultimo_contato": "Aguardando",
                "estacao": "Goldstone",
                "diagnostico": "Aguardando a primeira atualização.",
            }
        telemetria = self.historico_telemetria[-1]
        qualidade = telemetria["comunicacao_base"]
        latencia = telemetria["latencia_comunicacao_ms"]
        perda = telemetria["perda_pacotes_percentual"]
        if qualidade < 30 or perda > 25:
            status = "CRITICO"
            diagnostico = "O link com a base está em falha operacional."
        elif qualidade < 60 or latencia > 800 or perda > 10:
            status = "ATENCAO"
            diagnostico = "Link instável; monitorar a perda de pacotes e a latência."
        else:
            status = "ESTAVEL"
            diagnostico = "Comunicação dentro da faixa nominal."
        estacoes = ["Goldstone", "Madrid", "Canberra"]
        return {
            "status": status,
            "qualidade": qualidade,
            "latencia": latencia,
            "perda": perda,
            "ultimo_contato": f"T+{self.tempo_decorrido_min} min",
            "estacao": estacoes[self.atualizacao_atual % len(estacoes)],
            "diagnostico": diagnostico,
        }

    def comparar_ultima_atualizacao(self) -> list[dict[str, Any]]:
        if len(self.historico_telemetria) < 2:
            return []
        atual = self.historico_telemetria[-1]
        anterior = self.historico_telemetria[-2]
        energia_atual = self.historico_energia[-1]
        energia_anterior = self.historico_energia[-2]
        itens = [
            ("Temperatura", atual["temperatura_interna"] - anterior["temperatura_interna"], "°C", False),
            ("Bateria", atual["bateria"] - anterior["bateria"], "%", True),
            ("Comunicação", atual["comunicacao_base"] - anterior["comunicacao_base"], "%", True),
            ("Oxigênio", atual["oxigenio"] - anterior["oxigenio"], "%", True),
            ("Estabilidade", atual["estabilidade_operacional"] - anterior["estabilidade_operacional"], "%", True),
            ("Saldo energético", energia_atual["saldo_energia"] - energia_anterior["saldo_energia"], "W", True),
        ]
        comparacao = []
        for nome, delta, unidade, maior_melhor in itens:
            melhorou = delta >= 0 if maior_melhor else delta <= 0
            comparacao.append(
                {
                    "nome": nome,
                    "delta": round(delta, 2),
                    "unidade": unidade,
                    "tendencia": "melhorou" if melhorou else "piorou",
                }
            )
        return comparacao

    def simular_falha_critica(self) -> dict[str, Any] | None:
        if not self.missao_em_execucao:
            self.iniciar_simulacao()
        resultado = self.avancar_atualizacao()
        if resultado is None:
            return None
        telemetria = resultado["telemetria"]
        telemetria.update(
            {
                "temperatura_interna": max(telemetria["temperatura_interna"], 74.0),
                "comunicacao_base": min(telemetria["comunicacao_base"], 18.0),
                "bateria": min(telemetria["bateria"], 14.0),
                "oxigenio": min(telemetria["oxigenio"], 76.0),
                "estabilidade_operacional": min(telemetria["estabilidade_operacional"], 31.0),
                "latencia_comunicacao_ms": max(telemetria["latencia_comunicacao_ms"], 980.0),
                "perda_pacotes_percentual": max(telemetria["perda_pacotes_percentual"], 31.0),
            }
        )
        risco = calcular_pontuacao_risco(telemetria)
        energia = analisar_energia(telemetria)
        self.historico_risco[-1] = risco
        self.historico_energia[-1] = energia
        self.status_geral = self.classificar_status_geral(risco, energia)
        self.atualizar_modo_operacional()
        self.alertas_ativos = gerar_eventos_por_estado(
            self.motor_eventos,
            self.atualizacao_atual,
            self.tempo_decorrido_min,
            risco,
            energia,
        )
        self.motor_eventos.registrar_evento(
            self.atualizacao_atual,
            self.tempo_decorrido_min,
            "CRITICO",
            "Simulacao",
            "Falha crítica simulada acionada.",
            "Cenário de demonstração para resposta operacional.",
            "Executar prioridades P1 e P2 do cockpit.",
        )
        self.ultima_atualizacao = {"telemetria": telemetria, "risco": risco, "energia": energia}
        return self.ultima_atualizacao

    def recomendacoes_prioritarias(self) -> list[str]:
        if not self.historico_risco:
            return ["Iniciar o monitoramento da missão."]
        recs = gerar_recomendacoes_operacionais(self.historico_risco[-1])
        if self.historico_energia:
            recs.extend(self.historico_energia[-1]["recomendacoes"])
        return recs[:4]

    def gerar_analise_ia(self) -> dict[str, str]:
        analise = analisar_missao_com_ia(
            self,
            usar_ia=self.configuracao.fonte_dados == "ia_regras",
            timeout_s=self.configuracao.timeout_analise_ia,
        )
        analise["atualizacao"] = str(self.atualizacao_atual)
        self.historico_analise_ia.append(analise)
        return analise

    def aquecer_modelo_ia(self) -> dict[str, Any]:
        self.aquecimento_ia = aquecer_modelo_ollama(timeout_s=self.configuracao.timeout_analise_ia)
        return self.aquecimento_ia

    def dados_para_graficos(self) -> dict[str, list[float]]:
        tempo = [i * self.configuracao.intervalo_monitoramento_min for i in range(1, len(self.historico_telemetria) + 1)]
        return {
            "tempo": tempo,
            "risco": [r["pontuacao"] for r in self.historico_risco],
            "bateria": [t["bateria"] for t in self.historico_telemetria],
            "comunicacao": [t["comunicacao_base"] for t in self.historico_telemetria],
            "saldo_energia": [e["saldo_energia"] for e in self.historico_energia],
            "temperatura": [t["temperatura_interna"] for t in self.historico_telemetria],
            "oxigenio": [t["oxigenio"] for t in self.historico_telemetria],
            "estabilidade": [t["estabilidade_operacional"] for t in self.historico_telemetria],
            "geracao_solar": [t["geracao_solar"] for t in self.historico_telemetria],
            "consumo_total": [e["consumo_total"] for e in self.historico_energia],
            "autonomia": [e["autonomia_horas"] for e in self.historico_energia],
            "latencia": [t["latencia_comunicacao_ms"] for t in self.historico_telemetria],
            "perda_pacotes": [t["perda_pacotes_percentual"] for t in self.historico_telemetria],
        }

    def _calcular_fase(self) -> str:
        progresso = self.atualizacao_atual / max(1, self.total_atualizacoes)
        if progresso < 0.25:
            return "INICIO"
        if progresso < 0.75:
            return "CRUZEIRO"
        return "APROXIMACAO FINAL"
