from __future__ import annotations

from typing import Any


CAPACIDADE_BATERIA_WH = 5000.0


def calcular_consumo_total(telemetria: dict[str, float]) -> float:
    return (
        telemetria["consumo_suporte_vida"]
        + telemetria["consumo_comunicacao"]
        + telemetria["consumo_estabilidade"]
        + telemetria["consumo_pesquisa"]
    )


def calcular_saldo_energia(telemetria: dict[str, float]) -> float:
    return telemetria["geracao_solar"] - calcular_consumo_total(telemetria)


def calcular_autonomia(telemetria: dict[str, float], capacidade_bateria_wh: float = CAPACIDADE_BATERIA_WH) -> float:
    consumo = calcular_consumo_total(telemetria)
    if consumo <= 0:
        return 0.0
    energia_disponivel = capacidade_bateria_wh * (telemetria["bateria"] / 100)
    return energia_disponivel / consumo


def analisar_energia(telemetria: dict[str, float]) -> dict[str, Any]:
    consumo_total = calcular_consumo_total(telemetria)
    saldo = calcular_saldo_energia(telemetria)
    autonomia = calcular_autonomia(telemetria)
    bateria = telemetria["bateria"]

    status = classificar_estado_energia(bateria, saldo)
    modo = definir_modo_energetico(status)
    recomendacoes = recomendar_priorizacao_cargas(status)

    return {
        "consumo_total": round(consumo_total, 2),
        "saldo_energia": round(saldo, 2),
        "autonomia_horas": round(autonomia, 2),
        "status": status,
        "modo_energetico": modo,
        "recomendacoes": recomendacoes,
        "cargas": montar_painel_cargas(telemetria, status),
    }


def classificar_estado_energia(bateria: float, saldo_energia: float) -> str:
    if bateria < 20 and saldo_energia < 0:
        return "CRITICO"
    if bateria < 50 or saldo_energia < 0:
        return "ATENCAO"
    return "NORMAL"


def definir_modo_energetico(status: str) -> str:
    if status == "CRITICO":
        return "EMERGENCIA"
    if status == "ATENCAO":
        return "CONSERVACAO"
    return "OPERACAO NOMINAL"


def recomendar_priorizacao_cargas(status: str) -> list[str]:
    if status == "CRITICO":
        recomendacoes = [
            "Reduzir as cargas não essenciais.",
            "Preservar o suporte de oxigênio, a comunicação e a estabilidade.",
            "Direcionar a geração solar para a recuperação da bateria.",
        ]
        return recomendacoes
    if status == "ATENCAO":
        return ["Reduzir o consumo secundário.", "Monitorar o saldo energético e a autonomia."]
    return ["Manter a operação nominal e armazenar o excedente solar."]


def montar_painel_cargas(telemetria: dict[str, float], status_energia: str) -> list[dict[str, Any]]:
    reduzir_secundarias = status_energia in {"ATENCAO", "CRITICO"}
    reduzir_estabilidade = status_energia == "CRITICO"
    return [
        {
            "nome": "Suporte de oxigênio",
            "consumo": telemetria["consumo_suporte_vida"],
            "prioridade": "Essencial",
            "decisao": "Manter ativa",
        },
        {
            "nome": "Comunicação com a base",
            "consumo": telemetria["consumo_comunicacao"],
            "prioridade": "Essencial",
            "decisao": "Manter ativa",
        },
        {
            "nome": "Estabilidade operacional",
            "consumo": telemetria["consumo_estabilidade"],
            "prioridade": "Essencial",
            "decisao": "Reduzir parcialmente" if reduzir_estabilidade else "Manter ativa",
        },
        {
            "nome": "Controle térmico",
            "consumo": max(80.0, telemetria["consumo_suporte_vida"] * 0.55),
            "prioridade": "Essencial",
            "decisao": "Manter ativa",
        },
        {
            "nome": "Pesquisa / carga experimental",
            "consumo": telemetria["consumo_pesquisa"],
            "prioridade": "Não essencial",
            "decisao": "Reduzir" if reduzir_secundarias else "Manter ativa",
        },
    ]
