from __future__ import annotations

import math
import random
from typing import Any

from .configuracao_simulacao import ConfiguracaoMissao


CHAVES_TELEMETRIA = [
    "temperatura_interna",
    "comunicacao_base",
    "bateria",
    "oxigenio",
    "estabilidade_operacional",
    "geracao_solar",
    "consumo_suporte_vida",
    "consumo_comunicacao",
    "consumo_estabilidade",
    "consumo_pesquisa",
    "latencia_comunicacao_ms",
    "perda_pacotes_percentual",
]


def limitar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def gerar_telemetria(config: ConfiguracaoMissao, atualizacao: int) -> dict[str, float]:
    total = max(1, config.total_atualizacoes)
    progresso = limitar(atualizacao / total, 0, 1)
    ruido = random.uniform

    temperatura = 24 + ruido(-1.5, 1.5)
    comunicacao = config.comunicacao_inicial + ruido(-2, 2)
    bateria = config.energia_inicial - progresso * 10 + ruido(-1.0, 1.0)
    oxigenio = config.oxigenio_inicial - progresso * 3 + ruido(-0.8, 0.8)
    estabilidade = config.estabilidade_inicial - progresso * 4 + ruido(-1.5, 1.5)
    geracao = 560 - progresso * 80 + ruido(-20, 20)
    latencia = 180 + ruido(-20, 30)
    perda = 2 + ruido(0, 2)

    if config.perfil_risco == "degradacao_progressiva":
        temperatura += progresso * 13
        comunicacao -= progresso * 28
        bateria -= progresso * 35
        estabilidade -= progresso * 28
        geracao -= progresso * 220
        latencia += progresso * 260
        perda += progresso * 12
    elif config.perfil_risco == "comunicacao_instavel":
        oscilacao = math.sin(atualizacao * 1.7) * 18
        comunicacao += oscilacao - progresso * 8
        estabilidade -= max(0, -oscilacao) * 0.25
        latencia += abs(oscilacao) * 14
        perda += abs(oscilacao) * 0.55
    elif config.perfil_risco == "suporte_vida":
        temperatura += progresso * 10
        oxigenio -= progresso * 18
        bateria -= progresso * 16
    elif config.perfil_risco == "critico":
        pico = 0.70
        distancia = abs(progresso - pico)
        fator = max(0, 1 - distancia / 0.22)
        temperatura += fator * 42 + progresso * 5
        comunicacao -= fator * 55
        bateria -= progresso * 30 + fator * 32
        oxigenio -= fator * 28
        estabilidade -= fator * 45
        geracao -= fator * 380
        latencia += fator * 760
        perda += fator * 38
        if progresso > 0.78:
            temperatura -= (progresso - 0.78) * 20
            comunicacao += (progresso - 0.78) * 30
            estabilidade += (progresso - 0.78) * 20

    suporte_vida = 165 + max(0, temperatura - 30) * 1.4 + ruido(-5, 6)
    consumo_comunicacao = 85 + max(0, 70 - comunicacao) * 0.6 + ruido(-4, 5)
    consumo_estabilidade = 105 + max(0, 75 - estabilidade) * 0.7 + ruido(-4, 5)
    consumo_pesquisa = 90 if bateria >= 35 else 45

    return {
        "temperatura_interna": round(limitar(temperatura, -20, 90), 1),
        "comunicacao_base": round(limitar(comunicacao, 0, 100), 1),
        "bateria": round(limitar(bateria, 0, 100), 1),
        "oxigenio": round(limitar(oxigenio, 0, 100), 1),
        "estabilidade_operacional": round(limitar(estabilidade, 0, 100), 1),
        "geracao_solar": round(max(0, geracao), 1),
        "consumo_suporte_vida": round(max(0, suporte_vida), 1),
        "consumo_comunicacao": round(max(0, consumo_comunicacao), 1),
        "consumo_estabilidade": round(max(0, consumo_estabilidade), 1),
        "consumo_pesquisa": round(max(0, consumo_pesquisa), 1),
        "latencia_comunicacao_ms": round(max(0, latencia), 1),
        "perda_pacotes_percentual": round(limitar(perda, 0, 100), 1),
    }


def validar_telemetria(dados: dict[str, Any]) -> bool:
    return set(CHAVES_TELEMETRIA).issubset(dados)
