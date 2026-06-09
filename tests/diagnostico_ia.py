from __future__ import annotations

import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sistema_integrado.assistente_ia import (
    MODELO_PADRAO_OLLAMA,
    analisar_missao_com_ia,
    aquecer_modelo_ollama,
    diagnosticar_geracao_telemetria_ia,
    listar_modelos_ollama,
    verificar_status_ollama,
)
from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao
from sistema_integrado.gerador_telemetria import gerar_telemetria


def medir(funcao):
    inicio = time.perf_counter()
    resultado = funcao()
    return resultado, time.perf_counter() - inicio


def sim_nao(valor: bool) -> str:
    return "sim" if valor else "não"


def imprimir_diagnostico_telemetria(indice: int, diagnostico: dict) -> None:
    print(f"Telemetria {indice}")
    print(f"Tempo: {diagnostico['tempo_resposta_s']:.2f}s")
    print(f"Timeout usado: {diagnostico['timeout_usado']}s")
    print(f"Consulta: {'OK' if diagnostico['consulta_ok'] else 'timeout/erro'}")
    print(f"Validação: {'OK' if diagnostico['validacao_ok'] else diagnostico['motivo_validacao']}")
    print(f"Origem: {diagnostico['origem_final']}")
    if diagnostico["chaves_faltantes"]:
        print(f"Chaves faltantes: {', '.join(diagnostico['chaves_faltantes'])}")
    if diagnostico["chaves_recebidas"]:
        print(f"Chaves recebidas: {', '.join(diagnostico['chaves_recebidas'])}")
    if not diagnostico["consulta_ok"] or not diagnostico["validacao_ok"]:
        texto = diagnostico.get("texto_bruto", "")
        if texto:
            print("Texto bruto recebido:")
            print(texto[:900])
    print()


def main() -> None:
    print("=" * 72)
    print("DIAGNÓSTICO IA - MISSION CONTROL AI".center(72))
    print("=" * 72)
    print(f"Modelo: {MODELO_PADRAO_OLLAMA}")

    status, tempo_status = medir(verificar_status_ollama)
    modelos, tempo_modelos = medir(listar_modelos_ollama)
    print(f"Ollama online: {sim_nao(status['online'])} ({tempo_status:.2f}s)")
    print(f"Modelos encontrados: {', '.join(modelos) if modelos else 'nenhum'} ({tempo_modelos:.2f}s)")
    print(f"Modelo encontrado: {sim_nao(MODELO_PADRAO_OLLAMA in modelos)}")
    if status.get("erro"):
        print(f"Erro status: {status['erro']}")
    print()

    aquecimento, tempo_aquecimento = medir(aquecer_modelo_ollama)
    print("Aquecimento")
    print(f"Tempo: {tempo_aquecimento:.2f}s")
    print(f"Resultado: {'OK' if aquecimento['ok'] else 'falhou'}")
    print(f"Motivo: {aquecimento['motivo']}")
    print()

    config = criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras")
    diagnosticos = []
    for indice in range(1, 4):
        fallback = gerar_telemetria(config, indice)
        diagnostico = diagnosticar_geracao_telemetria_ia(config, indice, fallback)
        diagnosticos.append(diagnostico)
        imprimir_diagnostico_telemetria(indice, diagnostico)

    estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="regras"))
    estado.iniciar_simulacao()
    estado.avancar_atualizacao()
    analise, tempo_analise = medir(lambda: analisar_missao_com_ia(estado, usar_ia=True))
    print("Análise da missão")
    print(f"Tempo: {tempo_analise:.2f}s")
    print(f"Origem: {analise['origem']}")
    print(f"Resumo: {analise['resumo']}")
    if analise.get("erro_tecnico"):
        print(f"Erro técnico: {analise['erro_tecnico']}")
    print()

    validas = sum(1 for item in diagnosticos if item["validacao_ok"])
    fallbacks = sum(1 for item in diagnosticos if item["origem_final"] != "ia + regras")
    print("Resumo")
    print(f"Telemetrias válidas: {validas}/3")
    print(f"Fallbacks: {fallbacks}/3")
    if fallbacks:
        print("Motivos de fallback:")
        for item in diagnosticos:
            if item["origem_final"] != "ia + regras":
                faltantes = ", ".join(item["chaves_faltantes"]) or "nenhuma chave faltante"
                print(f"- {item['motivo_validacao']} | faltantes: {faltantes} | tempo: {item['tempo_resposta_s']:.2f}s")


if __name__ == "__main__":
    main()
