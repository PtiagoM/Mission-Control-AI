"""
MISSION CONTROL IA — Energy & Sustainability Monitor
Missão: Artemis Deep Scan

Aprofunda o sistema de energia da missão a partir dos ciclos do núcleo:
bateria, geração solar simulada, consumo, saldo energético, autonomia e modo operacional.
"""
from __future__ import annotations
from typing import Any

"""Importa dados da missão do core do sistema, caso não seja possível, cria novos dados simulados"""
try:
    from entregas_materias.automacao_python.mission_control_core import dados_missao, NOME_MISSAO, NOME_EQUIPE
except ImportError:
    NOME_MISSAO, NOME_EQUIPE = "Artemis Deep Scan", "Equipe 7"
    dados_missao = [[22, 95, 91, 98, 93], [26, 83, 75, 95, 87], [32, 68, 60, 92, 72],
                    [37, 44, 41, 85, 58], [40, 25, 17, 76, 33], [35, 52, 30, 81, 48]]

CAPACIDADE_BATERIA_WH = 5000.0

# Dados simulados especializados, correspondentes aos seis ciclos da missão.
dados_energia = [
    {"geracao_solar": 620, "suporte_vida": 170, "comunicacao": 85, "navegacao": 110, "pesquisa": 95},
    {"geracao_solar": 560, "suporte_vida": 170, "comunicacao": 90, "navegacao": 112, "pesquisa": 98},
    {"geracao_solar": 440, "suporte_vida": 175, "comunicacao": 92, "navegacao": 115, "pesquisa": 100},
    {"geracao_solar": 300, "suporte_vida": 180, "comunicacao": 98, "navegacao": 115, "pesquisa": 92},
    {"geracao_solar": 120, "suporte_vida": 185, "comunicacao": 105, "navegacao": 120, "pesquisa": 80},
    {"geracao_solar": 280, "suporte_vida": 178, "comunicacao": 92, "navegacao": 100, "pesquisa": 40},
]


def calcular_consumo_total(registro: dict[str, float]) -> float:
    return registro["suporte_vida"] + registro["comunicacao"] + registro["navegacao"] + registro["pesquisa"]


def calcular_autonomia_horas(bateria: float, consumo_total: float) -> float:
    energia_disponivel = CAPACIDADE_BATERIA_WH * (bateria / 100)
    return energia_disponivel / consumo_total if consumo_total else 0.0


def classificar_energia(bateria: float, saldo: float) -> tuple[str, str, list[str]]:
    if bateria < 20 and saldo < 0:
        return "CRÍTICO", "EMERGÊNCIA", [
            "Ativar modo de economia de energia.",
            "Suspender módulo experimental e cargas não essenciais.",
            "Priorizar suporte à vida, comunicação e estabilidade.",
        ]
    if bateria < 20:
        return "CRÍTICO", "ECONOMIA", [
            "Ativar modo de economia de energia.",
            "Direcionar geração disponível para recuperação da reserva.",
        ]
    if bateria < 50 or saldo < 0:
        return "ATENÇÃO", "CONSERVAÇÃO", [
            "Reduzir consumo do módulo experimental.",
            "Monitorar saldo energético e reserva da bateria.",
        ]
    return "NORMAL", "OPERAÇÃO NOMINAL", [
        "Manter operação e destinar excedente para a reserva energética."
    ]


def analisar_ciclo_energetico(numero: int) -> dict[str, Any]:
    bateria = dados_missao[numero - 1][2]
    registro = dados_energia[numero - 1]
    consumo = calcular_consumo_total(registro)
    saldo = registro["geracao_solar"] - consumo
    status, modo, recomendacoes = classificar_energia(bateria, saldo)
    return {
        "ciclo": numero, "bateria": bateria, "geracao_solar": registro["geracao_solar"],
        "suporte_vida": registro["suporte_vida"], "comunicacao": registro["comunicacao"],
        "navegacao": registro["navegacao"], "pesquisa": registro["pesquisa"],
        "consumo_total": consumo, "saldo": saldo,
        "autonomia": calcular_autonomia_horas(bateria, consumo),
        "status": status, "modo": modo, "recomendacoes": recomendacoes,
    }


def processar_energia() -> dict[str, Any]:
    ciclos = [analisar_ciclo_energetico(i) for i in range(1, len(dados_missao) + 1)]
    saldos = [c["saldo"] for c in ciclos]
    return {
        "missao": NOME_MISSAO, "equipe": NOME_EQUIPE, "ciclos": ciclos,
        "media_geracao": sum(c["geracao_solar"] for c in ciclos) / len(ciclos),
        "media_consumo": sum(c["consumo_total"] for c in ciclos) / len(ciclos),
        "saldo_total": sum(saldos),
        "ciclos_criticos": sum(c["status"] == "CRÍTICO" for c in ciclos),
        "ciclo_pior_saldo": saldos.index(min(saldos)) + 1, "pior_saldo": min(saldos),
    }


def imprimir_relatorio_energetico() -> None:
    resultado = processar_energia()
    print("=" * 80)
    print("MISSION CONTROL IA — ENERGY & SUSTAINABILITY MONITOR".center(80))
    print("=" * 80)
    print(f"Missão: {NOME_MISSAO} | Equipe: {NOME_EQUIPE}")
    print(f"Capacidade nominal da bateria: {CAPACIDADE_BATERIA_WH:.0f} Wh")
    for c in resultado["ciclos"]:
        print("\n" + "-" * 80)
        print(f"CICLO {c['ciclo']} — {c['status']} | MODO: {c['modo']}")
        print("-" * 80)
        print(f"Bateria: {c['bateria']:.1f}% | Geração solar: {c['geracao_solar']:.1f} W | Consumo total: {c['consumo_total']:.1f} W")
        print(f"Saldo energético: {c['saldo']:+.1f} W | Autonomia estimada: {c['autonomia']:.2f} h")
        print(f"Consumos — Suporte à vida: {c['suporte_vida']} W | Comunicação: {c['comunicacao']} W | Navegação: {c['navegacao']} W | Pesquisa: {c['pesquisa']} W")
        print("Recomendações:")
        for rec in c["recomendacoes"]:
            print(f"- {rec}")
    print("\n" + "=" * 80)
    print("RELATÓRIO ENERGÉTICO CONSOLIDADO")
    print("=" * 80)
    print(f"Geração solar média : {resultado['media_geracao']:.2f} W")
    print(f"Consumo médio       : {resultado['media_consumo']:.2f} W")
    print(f"Saldo acumulado     : {resultado['saldo_total']:+.2f} W")
    print(f"Ciclos críticos     : {resultado['ciclos_criticos']}")
    print(f"Pior déficit        : Ciclo {resultado['ciclo_pior_saldo']} ({resultado['pior_saldo']:+.2f} W)")
    print("Conclusão: a escassez energética crítica exige preservação de suporte à vida,")
    print("comunicação e estabilidade antes de cargas secundárias.")
    print("=" * 80)


if __name__ == "__main__":
    imprimir_relatorio_energetico()
