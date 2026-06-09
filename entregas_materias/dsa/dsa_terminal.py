"""
MISSION CONTROL AI - Terminal de Monitoramento Operacional
Missao: Artemis Deep Scan

Registra leituras simuladas, executa verificacoes automaticas e mantem
historico operacional no terminal. Pode importar dados do nucleo central.
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from entregas_materias.automacao_python.mission_control_core import NOME_EQUIPE, NOME_MISSAO, dados_missao
except ImportError:
    NOME_MISSAO, NOME_EQUIPE = "Artemis Deep Scan", "Equipe 7"
    dados_missao = [
        [22, 95, 91, 98, 93],
        [26, 83, 75, 95, 87],
        [32, 68, 60, 92, 72],
        [37, 44, 41, 85, 58],
        [40, 25, 17, 76, 33],
        [35, 52, 30, 81, 48],
    ]

COMUNICACAO_ATIVA = 1
FALHA_COMUNICACAO = 0
historico_leituras: list[dict[str, Any]] = []


def texto_comunicacao(valor: int) -> str:
    return "ATIVA" if valor == COMUNICACAO_ATIVA else "FALHA"


def converter_comunicacao_percentual(percentual: float) -> int:
    return FALHA_COMUNICACAO if percentual < 30 else COMUNICACAO_ATIVA


def analisar_leitura(temperatura: float, energia: float, comunicacao: int) -> dict[str, Any]:
    alertas: list[str] = []
    avisos: list[str] = []
    recomendacoes: list[str] = []

    if temperatura > 80:
        alertas.append("Alerta de superaquecimento.")
        recomendacoes.append("Ativar controle termico emergencial.")
    elif temperatura >= 70:
        avisos.append("Temperatura elevada.")
        recomendacoes.append("Intensificar monitoramento termico.")

    if energia < 20:
        alertas.append("Ativar economia de energia.")
        recomendacoes.append("Priorizar sistemas essenciais.")
    elif energia <= 30:
        avisos.append("Reserva energetica reduzida.")
        recomendacoes.append("Reduzir consumo nao essencial.")

    if comunicacao == FALHA_COMUNICACAO:
        alertas.append("Falha de comunicacao.")
        recomendacoes.append("Tentar restabelecer enlace com a base.")

    status = "CRITICO" if alertas else "ATENCAO" if avisos else "NORMAL"
    if status == "NORMAL":
        recomendacoes.append("Manter operacao normal.")
    return {"status": status, "alertas": alertas, "avisos": avisos, "recomendacoes": recomendacoes}


def registrar_leitura(temperatura: float, energia: float, comunicacao: int, origem: str = "Manual") -> dict[str, Any]:
    leitura = {
        "numero": len(historico_leituras) + 1,
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "origem": origem,
        "temperatura": temperatura,
        "energia": energia,
        "comunicacao": comunicacao,
        **analisar_leitura(temperatura, energia, comunicacao),
    }
    historico_leituras.append(leitura)
    return leitura


def ler_float(mensagem: str, minimo: float, maximo: float) -> float:
    while True:
        try:
            valor = float(input(mensagem).strip().replace(",", "."))
            if minimo <= valor <= maximo:
                return valor
            print(f"Informe um valor entre {minimo} e {maximo}.")
        except ValueError:
            print("Valor invalido. Digite um numero.")


def ler_comunicacao() -> int:
    while True:
        valor = input("Comunicacao (1 = ativa / 0 = falha): ").strip()
        if valor in {"0", "1"}:
            return int(valor)
        print("Valor invalido. Digite 1 ou 0.")


def inserir_leitura_manual() -> None:
    print("\nNOVA LEITURA OPERACIONAL")
    leitura = registrar_leitura(
        ler_float("Temperatura da nave (C): ", -100, 200),
        ler_float("Nivel de energia (%): ", 0, 100),
        ler_comunicacao(),
    )
    print(f"Leitura registrada. Status: {leitura['status']}")


def importar_ciclo_nucleo() -> None:
    print("\nCICLOS DA MISSAO PRINCIPAL")
    for i, ciclo in enumerate(dados_missao, start=1):
        print(f"{i}. Temperatura: {ciclo[0]} C | Energia: {ciclo[2]}% | Comunicacao: {ciclo[1]}%")
    while True:
        try:
            indice = int(input("Selecione o ciclo: "))
            if 1 <= indice <= len(dados_missao):
                ciclo = dados_missao[indice - 1]
                leitura = registrar_leitura(
                    ciclo[0],
                    ciclo[2],
                    converter_comunicacao_percentual(ciclo[1]),
                    f"Nucleo - Ciclo {indice}",
                )
                print(
                    f"Ciclo importado. Comunicacao: {texto_comunicacao(leitura['comunicacao'])} "
                    f"| Status: {leitura['status']}"
                )
                return
            print("Ciclo inexistente.")
        except ValueError:
            print("Digite um numero valido.")


def simular_evento_critico() -> None:
    leitura = registrar_leitura(84, 17, FALHA_COMUNICACAO, "Simulacao critica")
    print("\nEvento critico registrado: 84 C | Energia 17% | Comunicacao FALHA")
    print(f"Status: {leitura['status']}")


def visualizar_ultima_leitura() -> None:
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return
    leitura = historico_leituras[-1]
    print("\n" + "-" * 68)
    print(f"LEITURA {leitura['numero']} - STATUS {leitura['status']} - ORIGEM: {leitura['origem']}")
    print("-" * 68)
    print(
        f"Temperatura: {leitura['temperatura']:.1f} C | Energia: {leitura['energia']:.1f}% "
        f"| Comunicacao: {texto_comunicacao(leitura['comunicacao'])}"
    )


def executar_analise() -> None:
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return
    visualizar_ultima_leitura()
    leitura = historico_leituras[-1]
    print("\nANALISE AUTOMATICA")
    for item in leitura["alertas"]:
        print(f"[ALERTA] {item}")
    for item in leitura["avisos"]:
        print(f"[ATENCAO] {item}")
    if not leitura["alertas"] and not leitura["avisos"]:
        print("Nenhuma condicao de risco identificada.")
    print("Recomendacoes:")
    for item in leitura["recomendacoes"]:
        print(f"- {item}")


def mostrar_historico() -> None:
    if not historico_leituras:
        print("\nNenhuma leitura registrada.")
        return
    print("\nHISTORICO DE LEITURAS")
    print("-" * 88)
    print(f"{'#':<4}{'Origem':<23}{'Temperatura':<15}{'Energia':<12}{'Comunicacao':<15}{'Status':<12}")
    print("-" * 88)
    for leitura in historico_leituras:
        print(
            f"{leitura['numero']:<4}{leitura['origem']:<23}"
            f"{str(leitura['temperatura']) + ' C':<15}{str(leitura['energia']) + '%':<12}"
            f"{texto_comunicacao(leitura['comunicacao']):<15}{leitura['status']:<12}"
        )


def main() -> None:
    print("=" * 70)
    print("MISSION CONTROL AI - TERMINAL DE MONITORAMENTO OPERACIONAL".center(70))
    print("=" * 70)
    print(f"Missao: {NOME_MISSAO} | Equipe: {NOME_EQUIPE}")
    while True:
        print("\n1. Inserir nova leitura")
        print("2. Visualizar status atual")
        print("3. Executar analise automatica")
        print("4. Consultar historico")
        print("5. Simular evento critico")
        print("6. Importar ciclo do nucleo central")
        print("0. Encerrar")
        opcao = input("Escolha uma opcao: ").strip()
        if opcao == "1":
            inserir_leitura_manual()
        elif opcao == "2":
            visualizar_ultima_leitura()
        elif opcao == "3":
            executar_analise()
        elif opcao == "4":
            mostrar_historico()
        elif opcao == "5":
            simular_evento_critico()
        elif opcao == "6":
            importar_ciclo_nucleo()
        elif opcao == "0":
            print("Terminal encerrado com seguranca.")
            break
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    main()
