"""
MISSION CONTROL AI - Núcleo Central de Telemetria e Risco
Missão: Artemis Deep Scan

Analisa os ciclos oficiais da missão usando cinco variáveis centrais:
temperatura, comunicação, bateria, oxigênio e estabilidade.
O módulo executa em terminal e também expõe resultados para integração.
"""
from __future__ import annotations

from typing import Any

NOME_SISTEMA = "MISSION CONTROL AI"
NOME_MISSAO = "Artemis Deep Scan"
NOME_EQUIPE = "Equipe 7"

# Ordem: [temperatura, comunicacao, bateria, oxigenio, estabilidade]
dados_missao: list[list[float]] = [
    [22, 95, 91, 98, 93],
    [26, 83, 75, 95, 87],
    [32, 68, 60, 92, 72],
    [37, 44, 41, 85, 58],
    [40, 25, 17, 76, 33],
    [35, 52, 30, 81, 48],
]

areas_monitoradas = [
    "Temperatura interna",
    "Comunicação com a base",
    "Sistema de energia",
    "Suporte de oxigênio",
    "Estabilidade operacional",
]

nomes_variaveis = ["Temperatura", "Comunicação", "Bateria", "Oxigênio", "Estabilidade"]


def analisar_temperatura(valor: float) -> tuple[str, str, int]:
    if valor < 18:
        return "ATENÇÃO", "Temperatura abaixo do ideal", 1
    elif 18 <= valor <= 30:
        return "NORMAL", "Temperatura estável", 0
    elif 30 < valor <= 35:
        return "ATENÇÃO", "Temperatura elevada", 1
    return "CRÍTICO", "Risco de superaquecimento", 2


def analisar_comunicacao(valor: float) -> tuple[str, str, int]:
    if valor < 30:
        return "CRÍTICO", "Comunicação com a base em nível crítico", 2
    elif 30 <= valor <= 59:
        return "ATENÇÃO", "Comunicação instável", 1
    return "NORMAL", "Comunicação estável", 0


def analisar_bateria(valor: float) -> tuple[str, str, int]:
    if valor < 20:
        return "CRÍTICO", "Bateria em nível crítico", 2
    elif 20 <= valor <= 49:
        return "ATENÇÃO", "Bateria abaixo do recomendado", 1
    return "NORMAL", "Energia estável", 0


def analisar_oxigenio(valor: float) -> tuple[str, str, int]:
    if valor < 80:
        return "CRÍTICO", "Oxigênio em nível crítico", 2
    elif 80 <= valor <= 89:
        return "ATENÇÃO", "Oxigênio abaixo do ideal", 1
    return "NORMAL", "Oxigênio adequado", 0


def analisar_estabilidade(valor: float) -> tuple[str, str, int]:
    if valor < 40:
        return "CRÍTICO", "Estabilidade operacional crítica", 2
    elif 40 <= valor <= 69:
        return "ATENÇÃO", "Estabilidade operacional reduzida", 1
    return "NORMAL", "Estabilidade operacional adequada", 0


def classificar_ciclo(pontuacao: float) -> str:
    if 0 <= pontuacao < 3:
        return "MISSÃO ESTÁVEL"
    elif 3 <= pontuacao < 6:
        return "MISSÃO EM ATENÇÃO"
    return "MISSÃO CRÍTICA"

def gerar_recomendacao(resultados: list[tuple[str, str, int]]) -> str:
    criticos = [nomes_variaveis[i] for i, r in enumerate(resultados) if r[0] == "CRÍTICO"]
    atencoes = [nomes_variaveis[i] for i, r in enumerate(resultados) if r[0] == "ATENÇÃO"]
    acoes = {
        "Temperatura": "Verificar controle térmico da missão.",
        "Comunicação": "Tentar restabelecer contato com a base.",
        "Bateria": "Ativar modo de economia de energia.",
        "Oxigênio": "Acionar protocolo de suporte à vida.",
        "Estabilidade": "Reduzir operações não essenciais.",
    }

    if len(criticos) >= 3:
        return "Ativar modo de segurança e priorizar suporte à vida, energia e comunicação."
    elif criticos:
        return acoes[criticos[0]]
    elif atencoes:
        return f"Monitorar sistemas em atenção ({', '.join(atencoes)}) e preparar contingência."
    return "Manter operação normal e continuar monitoramento."


def analisar_ciclo(ciclo: list[float], numero: int) -> dict[str, Any]:
    temp, comm, bat, ox, estab = ciclo
    resultados = [
        analisar_temperatura(temp),
        analisar_comunicacao(comm),
        analisar_bateria(bat),
        analisar_oxigenio(ox),
        analisar_estabilidade(estab),
    ]
    risco = sum(item[2] for item in resultados)
    return {
        "numero": numero,
        "dados": {
            "temperatura": temp,
            "comunicacao": comm,
            "bateria": bat,
            "oxigenio": ox,
            "estabilidade": estab,
        },
        "resultados": resultados,
        "risco": risco,
        "classificacao": classificar_ciclo(risco),
        "recomendacao": gerar_recomendacao(resultados),
    }


def analisar_tendencia(riscos: list[int]) -> str:
    if riscos[-1] > riscos[0]:
        return "A missão apresentou tendência de piora."
    elif riscos[-1] < riscos[0]:
        return "A missão apresentou tendência de melhora."
    return "A missão permaneceu estável em relação ao início."


def identificar_area_mais_afetada(pontuacao_por_area: list[int]) -> tuple[str, int]:
    indice_area = pontuacao_por_area.index(max(pontuacao_por_area))
    return areas_monitoradas[indice_area], pontuacao_por_area[indice_area]


def gerar_conclusao(resultado: dict[str, Any]) -> str:
    if resultado["ciclos_criticos"] >= 2 or resultado["maior_risco"] >= 8:
        return (
            "A missão apresentou instabilidade relevante durante a operação. "
            "A equipe deve manter o plano de contingência ativo e priorizar os "
            "sistemas com maior pontuação de risco."
        )
    elif resultado["risco_medio"] >= 3:
        return (
            "A missão exige atenção operacional. Os sistemas devem continuar "
            "monitorados até a estabilização dos indicadores."
        )
    return "A missão permanece em condição estável, com monitoramento contínuo recomendado."


def processar_missao() -> dict[str, Any]:
    ciclos = [analisar_ciclo(ciclo, i + 1) for i, ciclo in enumerate(dados_missao)]
    riscos = [c["risco"] for c in ciclos]
    pontuacao_por_area = [sum(c["resultados"][i][2] for c in ciclos) for i in range(5)]
    medias = [sum(c[i] for c in dados_missao) / len(dados_missao) for i in range(5)]
    maior_risco = max(riscos)
    risco_medio = sum(riscos) / len(riscos)
    area_mais_afetada, pontos_area_mais_afetada = identificar_area_mais_afetada(pontuacao_por_area)

    resultado = {
        "missao": NOME_MISSAO,
        "equipe": NOME_EQUIPE,
        "ciclos": ciclos,
        "riscos": riscos,
        "medias": medias,
        "pontuacao_por_area": pontuacao_por_area,
        "ciclo_mais_critico": riscos.index(maior_risco) + 1,
        "maior_risco": maior_risco,
        "risco_medio": risco_medio,
        "ciclos_criticos": sum(r >= 6 for r in riscos),
        "tendencia": analisar_tendencia(riscos),
        "area_mais_afetada": area_mais_afetada,
        "pontos_area_mais_afetada": pontos_area_mais_afetada,
        "classificacao_final": classificar_ciclo(risco_medio),
    }
    resultado["conclusao"] = gerar_conclusao(resultado)
    return resultado


def gerar_relatorio_final(resultado: dict[str, Any]) -> None:
    medias = resultado["medias"]
    print("\n" + "=" * 72)
    print("RELATÓRIO FINAL DA MISSÃO")
    print("=" * 72)
    print(f"Missão: {resultado['missao']}")
    print(f"Equipe: {resultado['equipe']}")
    print(f"Quantidade de ciclos analisados: {len(resultado['ciclos'])}")
    print()
    print(f"Média de temperatura: {medias[0]:.2f} °C")
    print(f"Média de comunicação: {medias[1]:.2f}%")
    print(f"Média de bateria: {medias[2]:.2f}%")
    print(f"Média de oxigênio: {medias[3]:.2f}%")
    print(f"Média de estabilidade: {medias[4]:.2f}%")
    print()
    print(f"Ciclo mais crítico: Ciclo {resultado['ciclo_mais_critico']}")
    print(f"Maior pontuação de risco: {resultado['maior_risco']}")
    print(f"Risco médio da missão: {resultado['risco_medio']:.2f}")
    print(f"Quantidade de ciclos críticos: {resultado['ciclos_criticos']}")
    print()
    print("Tendência da missão:")
    print(resultado["tendencia"])
    print()
    print("Pontuação acumulada por área:")
    for area, pontos in zip(areas_monitoradas, resultado["pontuacao_por_area"]):
        print(f"{area}: {pontos} pontos")
    print()
    print("Área mais afetada:")
    print(resultado["area_mais_afetada"])
    print()
    print("Classificação final da missão:")
    print(resultado["classificacao_final"])
    print()
    print("Conclusão:")
    print(resultado["conclusao"])
    print("=" * 72)


def imprimir_relatorio() -> None:
    r = processar_missao()
    print("=" * 72)
    print(NOME_SISTEMA.center(72))
    print("=" * 72)
    print(f"Missão: {NOME_MISSAO}")
    print(f"Equipe: {NOME_EQUIPE}")
    print(f"Quantidade de ciclos analisados: {len(r['ciclos'])}")
    print("=" * 72)

    for ciclo in r["ciclos"]:
        d = ciclo["dados"]
        analises = ciclo["resultados"]
        print("\n" + "-" * 72)
        print(f"CICLO {ciclo['numero']}")
        print("-" * 72)
        for nome, valor, analise in [
            ("Temperatura", f"{d['temperatura']} °C", analises[0]),
            ("Comunicação", f"{d['comunicacao']}%", analises[1]),
            ("Bateria", f"{d['bateria']}%", analises[2]),
            ("Oxigênio", f"{d['oxigenio']}%", analises[3]),
            ("Estabilidade", f"{d['estabilidade']}%", analises[4]),
        ]:
            print(f"{nome}: {valor} | {analise[0]} | {analise[1]}")

        print()
        print(f"Pontuação de risco do ciclo: {ciclo['risco']}")
        print(f"Classificação do ciclo: {ciclo['classificacao']}")
        print(f"Recomendação: {ciclo['recomendacao']}")

    gerar_relatorio_final(r)


if __name__ == "__main__":
    imprimir_relatorio()
