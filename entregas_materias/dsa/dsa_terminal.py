"""
MISSION CONTROL IA - Terminal de Monitoramento Operacional
Missão: Artemis Deep Scan

Entrega individual de Data Structures and Algorithms / Programação Aplicada.

Este sistema executa no terminal e permite:
- inserir leituras da missão;
- simular leituras operacionais;
- analisar temperatura, energia, comunicação e status operacional;
- gerar alertas automáticos;
- manter histórico de leituras;
- demonstrar uso de listas, dicionários, funções, condicionais e repetição.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


NOME_SISTEMA = "MISSION CONTROL IA"
NOME_MISSAO = "Artemis Deep Scan"
NOME_EQUIPE = "Equipe 7"

COMUNICACAO_ATIVA = 1
FALHA_COMUNICACAO = 0

# Lista principal do sistema.
# Cada leitura registrada será armazenada como um dicionário dentro dessa lista.
historico_leituras: list[dict[str, Any]] = []


# Leituras simuladas próprias desta entrega.
# Não há importação de outros módulos do projeto.
leituras_simuladas: list[dict[str, Any]] = [
    {
        "temperatura": 24.0,
        "energia": 92.0,
        "comunicacao": COMUNICACAO_ATIVA,
        "status_operacional": "NOMINAL",
    },
    {
        "temperatura": 38.0,
        "energia": 64.0,
        "comunicacao": COMUNICACAO_ATIVA,
        "status_operacional": "ATENÇÃO",
    },
    {
        "temperatura": 72.0,
        "energia": 28.0,
        "comunicacao": COMUNICACAO_ATIVA,
        "status_operacional": "ATENÇÃO",
    },
    {
        "temperatura": 85.0,
        "energia": 16.0,
        "comunicacao": FALHA_COMUNICACAO,
        "status_operacional": "CRÍTICO",
    },
]


def texto_comunicacao(valor: int) -> str:
    """
    Converte o valor numérico da comunicação em texto.
    """
    return "ATIVA" if valor == COMUNICACAO_ATIVA else "FALHA"


def analisar_leitura(
    temperatura: float,
    energia: float,
    comunicacao: int,
    status_operacional: str,
) -> dict[str, Any]:
    """
    Analisa uma leitura da missão e retorna alertas, avisos,
    recomendações e classificação final.
    """
    alertas: list[str] = []
    avisos: list[str] = []
    recomendacoes: list[str] = []

    if temperatura > 80:
        alertas.append("Alerta de superaquecimento.")
        recomendacoes.append("Ativar controle térmico emergencial.")
    elif temperatura >= 70:
        avisos.append("Temperatura elevada.")
        recomendacoes.append("Intensificar monitoramento térmico.")

    if energia < 20:
        alertas.append("Energia em nível crítico.")
        recomendacoes.append("Ativar modo de economia de energia.")
        recomendacoes.append("Priorizar sistemas essenciais.")
    elif energia <= 30:
        avisos.append("Reserva energética reduzida.")
        recomendacoes.append("Reduzir consumo não essencial.")

    if comunicacao == FALHA_COMUNICACAO:
        alertas.append("Falha de comunicação.")
        recomendacoes.append("Tentar restabelecer contato com a base.")

    if status_operacional.upper() == "CRÍTICO":
        alertas.append("Status operacional crítico.")
        recomendacoes.append("Executar protocolo de contingência.")
    elif status_operacional.upper() == "ATENÇÃO":
        avisos.append("Status operacional em atenção.")
        recomendacoes.append("Manter acompanhamento contínuo da missão.")

    if alertas:
        classificacao = "CRÍTICO"
    elif avisos:
        classificacao = "ATENÇÃO"
    else:
        classificacao = "NORMAL"
        recomendacoes.append("Manter operação normal e continuar monitoramento.")

    return {
        "classificacao": classificacao,
        "alertas": alertas,
        "avisos": avisos,
        "recomendacoes": recomendacoes,
    }


def registrar_leitura(
    temperatura: float,
    energia: float,
    comunicacao: int,
    status_operacional: str,
    origem: str,
) -> dict[str, Any]:
    """
    Registra uma nova leitura no histórico da missão.
    """
    analise = analisar_leitura(
        temperatura,
        energia,
        comunicacao,
        status_operacional,
    )

    leitura = {
        "numero": len(historico_leituras) + 1,
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "origem": origem,
        "temperatura": temperatura,
        "energia": energia,
        "comunicacao": comunicacao,
        "status_operacional": status_operacional,
        **analise,
    }

    historico_leituras.append(leitura)
    return leitura


def ler_float(mensagem: str, minimo: float, maximo: float) -> float:
    """
    Lê um número decimal dentro de uma faixa válida.
    """
    while True:
        try:
            valor = float(input(mensagem).strip().replace(",", "."))

            if minimo <= valor <= maximo:
                return valor

            print(f"Informe um valor entre {minimo} e {maximo}.")

        except ValueError:
            print("Valor inválido. Digite um número.")


def ler_comunicacao() -> int:
    """
    Lê o status da comunicação.
    """
    while True:
        valor = input("Comunicação (1 = ativa / 0 = falha): ").strip()

        if valor in {"0", "1"}:
            return int(valor)

        print("Valor inválido. Digite 1 ou 0.")


def ler_status_operacional() -> str:
    """
    Lê o status operacional da missão.
    """
    opcoes_validas = {"NORMAL", "ATENÇÃO", "ATENCAO", "CRÍTICO", "CRITICO"}

    while True:
        valor = input("Status operacional (NORMAL / ATENÇÃO / CRÍTICO): ").strip().upper()

        if valor in opcoes_validas:
            if valor == "ATENCAO":
                return "ATENÇÃO"
            if valor == "CRITICO":
                return "CRÍTICO"
            return valor

        print("Status inválido. Digite NORMAL, ATENÇÃO ou CRÍTICO.")


def inserir_leitura_manual() -> None:
    """
    Permite inserir uma nova leitura manualmente.
    """
    print("\nNOVA LEITURA OPERACIONAL")
    print("-" * 70)

    temperatura = ler_float("Temperatura da nave (°C): ", -100, 200)
    energia = ler_float("Nível de energia (%): ", 0, 100)
    comunicacao = ler_comunicacao()
    status_operacional = ler_status_operacional()

    leitura = registrar_leitura(
        temperatura,
        energia,
        comunicacao,
        status_operacional,
        origem="Manual",
    )

    print(f"\nLeitura registrada com sucesso. Classificação: {leitura['classificacao']}")


def simular_leitura_operacional() -> None:
    """
    Permite escolher uma leitura simulada já preparada para demonstração.
    """
    print("\nLEITURAS SIMULADAS DISPONÍVEIS")
    print("-" * 70)

    for indice, leitura in enumerate(leituras_simuladas, start=1):
        print(
            f"{indice}. Temperatura: {leitura['temperatura']} °C | "
            f"Energia: {leitura['energia']}% | "
            f"Comunicação: {texto_comunicacao(leitura['comunicacao'])} | "
            f"Status: {leitura['status_operacional']}"
        )

    while True:
        try:
            escolha = int(input("Escolha uma leitura simulada: "))

            if 1 <= escolha <= len(leituras_simuladas):
                leitura_base = leituras_simuladas[escolha - 1]

                leitura = registrar_leitura(
                    leitura_base["temperatura"],
                    leitura_base["energia"],
                    leitura_base["comunicacao"],
                    leitura_base["status_operacional"],
                    origem=f"Simulação {escolha}",
                )

                print(f"\nLeitura simulada registrada. Classificação: {leitura['classificacao']}")
                return

            print("Opção inexistente.")

        except ValueError:
            print("Digite um número válido.")


def simular_evento_critico() -> None:
    """
    Registra automaticamente uma situação crítica para demonstrar os alertas.
    """
    leitura = registrar_leitura(
        temperatura=86.0,
        energia=14.0,
        comunicacao=FALHA_COMUNICACAO,
        status_operacional="CRÍTICO",
        origem="Evento crítico",
    )

    print("\nEVENTO CRÍTICO REGISTRADO")
    print("-" * 70)
    print("Temperatura: 86.0 °C | Energia: 14.0% | Comunicação: FALHA")
    print(f"Classificação: {leitura['classificacao']}")


def visualizar_ultima_leitura() -> None:
    """
    Exibe a última leitura registrada no histórico.
    """
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return

    leitura = historico_leituras[-1]

    print("\n" + "-" * 70)
    print(f"LEITURA {leitura['numero']} — STATUS {leitura['classificacao']}")
    print("-" * 70)
    print(f"Data/hora           : {leitura['data_hora']}")
    print(f"Origem              : {leitura['origem']}")
    print(f"Temperatura         : {leitura['temperatura']:.1f} °C")
    print(f"Energia             : {leitura['energia']:.1f}%")
    print(f"Comunicação         : {texto_comunicacao(leitura['comunicacao'])}")
    print(f"Status operacional  : {leitura['status_operacional']}")


def executar_analise() -> None:
    """
    Executa a análise automática da última leitura registrada.
    """
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return

    visualizar_ultima_leitura()

    leitura = historico_leituras[-1]

    print("\nANÁLISE AUTOMÁTICA")
    print("-" * 70)

    if leitura["alertas"]:
        print("Alertas:")
        for alerta in leitura["alertas"]:
            print(f"[ALERTA] {alerta}")

    if leitura["avisos"]:
        print("\nAvisos:")
        for aviso in leitura["avisos"]:
            print(f"[ATENÇÃO] {aviso}")

    if not leitura["alertas"] and not leitura["avisos"]:
        print("Nenhuma condição de risco identificada.")

    print("\nRecomendações:")
    for recomendacao in leitura["recomendacoes"]:
        print(f"- {recomendacao}")


def mostrar_historico() -> None:
    """
    Exibe todas as leituras registradas durante a execução.
    """
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return

    print("\nHISTÓRICO DE LEITURAS")
    print("-" * 105)
    print(
        f"{'#':<4}"
        f"{'Origem':<18}"
        f"{'Temp.':<12}"
        f"{'Energia':<12}"
        f"{'Comunicação':<15}"
        f"{'Status Op.':<16}"
        f"{'Classificação':<15}"
    )
    print("-" * 105)

    for leitura in historico_leituras:
        print(
            f"{leitura['numero']:<4}"
            f"{leitura['origem']:<18}"
            f"{str(leitura['temperatura']) + ' °C':<12}"
            f"{str(leitura['energia']) + '%':<12}"
            f"{texto_comunicacao(leitura['comunicacao']):<15}"
            f"{leitura['status_operacional']:<16}"
            f"{leitura['classificacao']:<15}"
        )


def exibir_resumo_geral() -> None:
    """
    Exibe um resumo quantitativo do histórico.
    """
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return

    total = len(historico_leituras)
    normais = sum(1 for leitura in historico_leituras if leitura["classificacao"] == "NORMAL")
    atencoes = sum(1 for leitura in historico_leituras if leitura["classificacao"] == "ATENÇÃO")
    criticos = sum(1 for leitura in historico_leituras if leitura["classificacao"] == "CRÍTICO")

    temperatura_media = sum(leitura["temperatura"] for leitura in historico_leituras) / total
    energia_media = sum(leitura["energia"] for leitura in historico_leituras) / total

    print("\nRESUMO GERAL DA MISSÃO")
    print("-" * 70)
    print(f"Total de leituras registradas : {total}")
    print(f"Leituras normais              : {normais}")
    print(f"Leituras em atenção           : {atencoes}")
    print(f"Leituras críticas             : {criticos}")
    print(f"Temperatura média             : {temperatura_media:.2f} °C")
    print(f"Energia média                 : {energia_media:.2f}%")


def exibir_menu() -> None:
    """
    Exibe o menu principal.
    """
    print("\nMENU PRINCIPAL")
    print("-" * 70)
    print("1. Inserir nova leitura manual")
    print("2. Simular leitura operacional")
    print("3. Visualizar status atual")
    print("4. Executar análise automática")
    print("5. Consultar histórico")
    print("6. Exibir resumo geral")
    print("7. Simular evento crítico")
    print("0. Encerrar sistema")


def main() -> None:
    """
    Fluxo principal do sistema.
    Mantém o menu em repetição até o usuário encerrar.
    """
    print("=" * 70)
    print("MISSION CONTROL IA - TERMINAL DE MONITORAMENTO OPERACIONAL".center(70))
    print("=" * 70)
    print(f"Missão: {NOME_MISSAO}")
    print(f"Equipe: {NOME_EQUIPE}")

    while True:
        exibir_menu()
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            inserir_leitura_manual()
        elif opcao == "2":
            simular_leitura_operacional()
        elif opcao == "3":
            visualizar_ultima_leitura()
        elif opcao == "4":
            executar_analise()
        elif opcao == "5":
            mostrar_historico()
        elif opcao == "6":
            exibir_resumo_geral()
        elif opcao == "7":
            simular_evento_critico()
        elif opcao == "0":
            print("\nSistema encerrado com segurança.")
            break
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()