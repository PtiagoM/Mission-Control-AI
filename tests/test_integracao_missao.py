from __future__ import annotations

import unittest

from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao
from sistema_integrado.relatorio_missao import gerar_relatorio


class TestIntegracaoMissao(unittest.TestCase):
    def test_fluxo_emergencia_completo(self) -> None:
        config = criar_configuracao_por_preset("Emergencia Simulada")
        estado = EstadoMissao(config)
        estado.iniciar_simulacao()
        estado.executar_ate_o_fim()
        self.assertEqual(config.total_atualizacoes, len(estado.historico_telemetria))
        self.assertEqual(config.total_atualizacoes, len(estado.historico_energia))
        self.assertTrue(any(e["severidade"] == "CRITICO" for e in estado.historico_eventos))
        self.assertTrue(estado.missao_finalizada)
        self.assertIn("maior_risco", gerar_relatorio(estado))

    def test_orbita_terrestre_comeca_baixo_risco(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        self.assertLessEqual(estado.historico_risco[-1]["pontuacao"], 2)
        dados = estado.dados_para_graficos()
        self.assertEqual(len(dados["tempo"]), len(dados["risco"]))
        self.assertEqual(len(dados["tempo"]), len(dados["bateria"]))


if __name__ == "__main__":
    unittest.main()
