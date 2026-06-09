from __future__ import annotations

import unittest

from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao
from sistema_integrado.relatorio_missao import formatar_relatorio_texto
from tests import benchmark_ia, diagnostico_ia


class TestSistemaIntegradoFinal(unittest.TestCase):
    def test_comparacao_e_comunicacao(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Sobrevoo Lunar"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        estado.avancar_atualizacao()
        self.assertTrue(estado.comparar_ultima_atualizacao())
        comunicacao = estado.analise_comunicacao_atual()
        self.assertIn(comunicacao["status"], {"ESTAVEL", "ATENCAO", "CRITICO"})
        self.assertIn(comunicacao["estacao"], {"Goldstone", "Madrid", "Canberra"})

    def test_falha_critica_simulada_e_relatorio(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        estado.simular_falha_critica()
        self.assertTrue(any(evento["severidade"] == "CRITICO" for evento in estado.historico_eventos))
        self.assertIn(estado.status_geral, {"CRITICO", "CONTINGENCIA"})
        texto = formatar_relatorio_texto(estado)
        self.assertIn("MISSION CONTROL AI", texto)
        self.assertIn("RECOMENDAÇÕES FINAIS", texto)
        self.assertIn("ANÁLISE COMPLEMENTAR DA IA", texto)
        self.assertIn("COMUNICAÇÃO", texto)

    def test_relatorio_ia_nao_executada_sem_erro_bruto(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        texto = formatar_relatorio_texto(estado)
        self.assertIn("ANÁLISE COMPLEMENTAR DA IA", texto)
        self.assertIn("Análise por IA não executada nesta simulação.", texto)
        self.assertNotIn("HTTP Error", texto)

    def test_benchmark_ia_existe_em_tests(self) -> None:
        self.assertTrue(callable(benchmark_ia.main))
        self.assertTrue(callable(diagnostico_ia.main))


if __name__ == "__main__":
    unittest.main()
