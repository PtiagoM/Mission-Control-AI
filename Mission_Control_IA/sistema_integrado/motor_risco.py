from __future__ import annotations

from typing import Any


AREAS_MONITORADAS = {
    "temperatura_interna": "Temperatura interna",
    "comunicacao_base": "Comunicação com a base",
    "bateria": "Sistema de energia",
    "oxigenio": "Suporte de oxigênio",
    "estabilidade_operacional": "Estabilidade operacional",
}


def analisar_temperatura(valor: float) -> tuple[str, int, str]:
    if valor < 18:
        return "ATENCAO", 1, "Temperatura abaixo do ideal."
    if 18 <= valor <= 30:
        return "NORMAL", 0, "Temperatura estável."
    if 30 < valor <= 35:
        return "ATENCAO", 1, "Temperatura elevada."
    return "CRITICO", 2, "Risco de superaquecimento."


def analisar_comunicacao(valor: float) -> tuple[str, int, str]:
    if valor < 30:
        return "CRITICO", 2, "Comunicação com a base em nível crítico."
    if 30 <= valor <= 59:
        return "ATENCAO", 1, "Comunicação instável."
    return "NORMAL", 0, "Comunicação estável."


def analisar_bateria(valor: float) -> tuple[str, int, str]:
    if valor < 20:
        return "CRITICO", 2, "Bateria em nível crítico."
    if 20 <= valor <= 49:
        return "ATENCAO", 1, "Bateria abaixo do recomendado."
    return "NORMAL", 0, "Energia estável."


def analisar_oxigenio(valor: float) -> tuple[str, int, str]:
    if valor < 80:
        return "CRITICO", 2, "Oxigênio em nível crítico."
    if 80 <= valor <= 89:
        return "ATENCAO", 1, "Oxigênio abaixo do ideal."
    return "NORMAL", 0, "Oxigênio adequado."


def analisar_estabilidade(valor: float) -> tuple[str, int, str]:
    if valor < 40:
        return "CRITICO", 2, "Estabilidade operacional crítica."
    if 40 <= valor <= 69:
        return "ATENCAO", 1, "Estabilidade operacional reduzida."
    return "NORMAL", 0, "Estabilidade operacional adequada."


def calcular_pontuacao_risco(telemetria: dict[str, float]) -> dict[str, Any]:
    analises = {
        "temperatura_interna": analisar_temperatura(telemetria["temperatura_interna"]),
        "comunicacao_base": analisar_comunicacao(telemetria["comunicacao_base"]),
        "bateria": analisar_bateria(telemetria["bateria"]),
        "oxigenio": analisar_oxigenio(telemetria["oxigenio"]),
        "estabilidade_operacional": analisar_estabilidade(telemetria["estabilidade_operacional"]),
    }
    pontuacao = sum(item[1] for item in analises.values())
    if pontuacao <= 2:
        status = "NOMINAL"
    elif pontuacao <= 5:
        status = "ATENCAO"
    elif pontuacao <= 8:
        status = "CRITICO"
    else:
        status = "CONTINGENCIA"
    return {"pontuacao": pontuacao, "status": status, "analises": analises}


def identificar_area_mais_afetada(historico_risco: list[dict[str, Any]]) -> dict[str, Any]:
    acumulado = {chave: 0 for chave in AREAS_MONITORADAS}
    for risco in historico_risco:
        for chave, analise in risco["analises"].items():
            acumulado[chave] += analise[1]
    chave_area = max(acumulado, key=acumulado.get)
    return {"area": AREAS_MONITORADAS[chave_area], "pontos": acumulado[chave_area]}


def gerar_recomendacoes_operacionais(risco: dict[str, Any]) -> list[str]:
    recomendacoes: list[str] = []
    for chave, analise in risco["analises"].items():
        status, _, _mensagem = analise
        area = AREAS_MONITORADAS[chave]
        if status == "CRITICO":
            recomendacoes.append(f"{area}: aplicar contingência imediata.")
        elif status == "ATENCAO":
            recomendacoes.append(f"{area}: intensificar monitoramento.")
    return recomendacoes or ["Manter a operação nominal e o monitoramento contínuo."]
