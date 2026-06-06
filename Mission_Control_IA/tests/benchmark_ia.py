from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sistema_integrado.assistente_ia import (
    MODELO_PADRAO_OLLAMA,
    gerar_telemetria_ia_com_fallback,
    listar_modelos_ollama,
    verificar_status_ollama,
    analisar_missao_com_ia,
)
from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao
from sistema_integrado.gerador_telemetria import gerar_telemetria


def medir(funcao):
    inicio = time.perf_counter()
    resultado = funcao()
    return resultado, time.perf_counter() - inicio


def imprimir_linha(label: str, valor: str) -> None:
    print(f"{label}: {valor}")


def main() -> None:
    print("=" * 64)
    print("BENCHMARK IA".center(64))
    print("=" * 64)
    imprimir_linha("Modelo", MODELO_PADRAO_OLLAMA)
    print()

    status, tempo_status = medir(verificar_status_ollama)
    imprimir_linha("Status Ollama", f"{'online' if status['online'] else 'offline'} em {tempo_status:.2f}s")

    modelos, tempo_modelos = medir(listar_modelos_ollama)
    imprimir_linha("Listagem de modelos", f"{tempo_modelos:.2f}s")
    imprimir_linha("Modelo encontrado", "sim" if MODELO_PADRAO_OLLAMA in modelos else "nao")
    if status.get("erro"):
        imprimir_linha("Erro status", status["erro"])
    print()

    config = criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras")
    tempos_telemetria: list[float] = []
    respostas_validas = 0
    fallbacks = 0

    for atualizacao in range(1, 4):
        fallback = gerar_telemetria(config, atualizacao)
        resultado, duracao = medir(lambda a=atualizacao, f=fallback: gerar_telemetria_ia_com_fallback(config, a, f))
        tempos_telemetria.append(duracao)
        origem = resultado["origem"]
        if origem == "ia + regras":
            respostas_validas += 1
        else:
            fallbacks += 1
        print(f"Telemetria {atualizacao}:")
        imprimir_linha("Tempo", f"{duracao:.2f}s")
        imprimir_linha("Validacao", resultado["validacao"])
        imprimir_linha("Origem", origem)
        print()

    media = statistics.mean(tempos_telemetria) if tempos_telemetria else 0
    imprimir_linha("Media telemetria", f"{media:.2f}s")
    imprimir_linha("Respostas validas", str(respostas_validas))
    imprimir_linha("Fallbacks", str(fallbacks))
    print()

    estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="regras"))
    estado.iniciar_simulacao()
    estado.avancar_atualizacao()
    analise, tempo_analise = medir(lambda: analisar_missao_com_ia(estado, usar_ia=True))
    print("Analise da missao:")
    imprimir_linha("Tempo", f"{tempo_analise:.2f}s")
    imprimir_linha("Origem", analise["origem"])
    imprimir_linha("Resumo", analise["resumo"])
    print()

    escala_sugerida = max(1, round(media + 1))
    print("Recomendacao:")
    imprimir_linha("Escala real minima sugerida", f"{escala_sugerida}s por atualizacao")
    if fallbacks:
        print("A IA usou fallback em parte do teste. Considere aumentar timeout ou aquecer o modelo antes da missao.")


if __name__ == "__main__":
    main()
