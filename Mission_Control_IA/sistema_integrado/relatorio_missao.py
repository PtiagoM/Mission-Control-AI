from __future__ import annotations

"""Relatorio textual consolidado da missao.

O relatorio transforma o estado acumulado da simulacao em um texto exportavel
para apresentacao: dados da missao, resultado operacional, energia,
comunicacao, alertas, recomendacoes e analise complementar da IA quando ela foi
efetivamente acionada.
"""

from typing import Any

from .assistente_ia import TIMEOUT_RELATORIO_IA, analisar_missao_com_ia
from .estado_missao import EstadoMissao
from .motor_risco import identificar_area_mais_afetada


def gerar_relatorio(estado: EstadoMissao) -> dict[str, Any]:
    """Calcula os indicadores finais usados pelo relatorio exportavel."""
    maior_risco = max((r["pontuacao"] for r in estado.historico_risco), default=0)
    atualizacao_critica = 0
    if estado.historico_risco:
        atualizacao_critica = max(range(len(estado.historico_risco)), key=lambda i: estado.historico_risco[i]["pontuacao"]) + 1
    menor_autonomia = min((e["autonomia_horas"] for e in estado.historico_energia), default=0)
    pior_saldo = min((e["saldo_energia"] for e in estado.historico_energia), default=0)
    area = identificar_area_mais_afetada(estado.historico_risco) if estado.historico_risco else {"area": "Sem dados", "pontos": 0}
    comunicacao = estado.analise_comunicacao_atual()
    return {
        "nome_missao": estado.configuracao.nome_missao,
        "tipo_missao": estado.configuracao.perfil_risco,
        "duracao_configurada": estado.configuracao.duracao_minutos,
        "intervalo_monitoramento": estado.configuracao.intervalo_monitoramento_min,
        "escala_execucao": estado.configuracao.escala_execucao_real_s,
        "atualizacoes_realizadas": len(estado.historico_telemetria),
        "status_final": estado.status_geral,
        "maior_risco": maior_risco,
        "atualizacao_mais_critica": atualizacao_critica,
        "area_mais_afetada": area["area"],
        "menor_autonomia": menor_autonomia,
        "pior_saldo_energetico": pior_saldo,
        "alertas_criticos": sum(1 for e in estado.historico_eventos if e["severidade"] == "CRITICO"),
        "total_eventos": len(estado.historico_eventos),
        "comunicacao": comunicacao,
        "conclusao_operacional": gerar_conclusao_operacional(estado, maior_risco, pior_saldo),
        "recomendacoes_finais": estado.recomendacoes_prioritarias(),
    }


def gerar_conclusao_operacional(estado: EstadoMissao, maior_risco: float, pior_saldo: float) -> str:
    """Resume o resultado operacional sem depender da IA."""
    if estado.status_geral in {"CONTINGENCIA", "CRITICO"} or maior_risco >= 6:
        return "A missão exigiu resposta operacional ativa, com prioridade para energia, comunicação e suporte de vida."
    if pior_saldo < 0:
        return "A missão permaneceu controlada, mas houve déficit energético que exige conservação de cargas."
    return "A missão permaneceu em condição nominal, com monitoramento contínuo recomendado."


def formatar_relatorio_texto(estado: EstadoMissao, timeout_ia: float | None = None) -> str:
    """Gera o texto final do relatorio e aciona IA apenas quando configurada."""
    relatorio = gerar_relatorio(estado)
    usar_ia = estado.configuracao.fonte_dados == "ia_regras"
    analise_ia = analisar_missao_com_ia(
        estado,
        usar_ia=usar_ia,
        timeout_s=timeout_ia or TIMEOUT_RELATORIO_IA,
    )
    comunicacao = relatorio["comunicacao"]
    linhas = [
        "MISSION CONTROL AI - RELATÓRIO DA MISSÃO",
        "=" * 64,
        "",
        "DADOS DA MISSÃO",
        "-" * 64,
        f"Missão: {relatorio['nome_missao']}",
        f"Tipo/perfil: {relatorio['tipo_missao']}",
        f"Duração configurada: {relatorio['duracao_configurada']} min",
        f"Intervalo de monitoramento: {relatorio['intervalo_monitoramento']} min",
        f"Escala de execução: {relatorio['escala_execucao']} s por atualização",
        f"Atualizações realizadas: {relatorio['atualizacoes_realizadas']}",
        "",
        "RESULTADO OPERACIONAL",
        "-" * 64,
        f"Status final: {relatorio['status_final']}",
        f"Maior risco registrado: {relatorio['maior_risco']}",
        f"Atualização mais crítica: {relatorio['atualizacao_mais_critica']}",
        f"Área mais afetada: {relatorio['area_mais_afetada']}",
        "",
        "ENERGIA",
        "-" * 64,
        f"Menor autonomia: {relatorio['menor_autonomia']:.2f} h",
        f"Pior saldo energético: {relatorio['pior_saldo_energetico']:.2f} W",
        "",
        "COMUNICAÇÃO",
        "-" * 64,
        f"Status do link: {comunicacao['status']}",
        f"Qualidade do sinal: {comunicacao['qualidade']:.1f}%",
        f"Latência: {comunicacao['latencia']:.1f} ms",
        f"Perda de pacotes: {comunicacao['perda']:.1f}%",
        f"Estação base: {comunicacao['estacao']}",
        f"Diagnóstico: {comunicacao['diagnostico']}",
        "",
        "ALERTAS",
        "-" * 64,
        f"Total de eventos: {relatorio['total_eventos']}",
        f"Alertas críticos: {relatorio['alertas_criticos']}",
        "",
        "CONCLUSÃO OPERACIONAL",
        "-" * 64,
        relatorio["conclusao_operacional"],
        "",
        "RECOMENDAÇÕES FINAIS",
        "-" * 64,
    ]
    linhas.extend(f"- {item}" for item in relatorio["recomendacoes_finais"])
    linhas.extend(_formatar_analise_ia_relatorio(analise_ia, usar_ia))
    return "\n".join(linhas)


def _formatar_analise_ia_relatorio(analise_ia: dict[str, str], ia_configurada: bool) -> list[str]:
    """Formata a parte complementar sem expor erro bruto do modelo."""
    linhas = ["", "ANÁLISE COMPLEMENTAR DA IA", "-" * 64]
    if not ia_configurada:
        linhas.append("Análise por IA não executada nesta simulação.")
        return linhas
    if analise_ia.get("origem") != "IA":
        linhas.extend(
            [
                "Análise por IA indisponível nesta chamada. Exibindo análise determinística.",
                f"Origem: {analise_ia.get('origem', 'fallback determinístico')}",
                "",
                "Resumo:",
                analise_ia["resumo"],
                "",
                "Próxima ação recomendada:",
                analise_ia["proxima_acao"],
            ]
        )
        return linhas

    linhas.extend(
        [
            "Origem: IA",
            f"Modelo: {analise_ia.get('modelo', 'llama3.2:1b')}",
            "",
            "Resumo:",
            analise_ia["resumo"],
            "",
            "Principal risco:",
            analise_ia["principal_risco"],
            "",
            "Justificativa:",
            analise_ia["justificativa"],
            "",
            "Prioridade operacional:",
            analise_ia["prioridade_operacional"],
            "",
            "Próxima ação recomendada:",
            analise_ia["proxima_acao"],
            "",
            "Observação da IA:",
            analise_ia["observacao"],
        ]
    )
    return linhas
