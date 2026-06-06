from __future__ import annotations

import random
import unittest

from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.gerador_telemetria import CHAVES_TELEMETRIA, gerar_telemetria
from sistema_integrado.motor_risco import calcular_pontuacao_risco


class TestGeradorTelemetria(unittest.TestCase):
    def test_chaves_obrigatorias(self) -> None:
        random.seed(1)
        config = criar_configuracao_por_preset("Orbita Terrestre")
        dado = gerar_telemetria(config, 1)
        self.assertEqual(set(CHAVES_TELEMETRIA), set(dado))

    def test_valores_dentro_dos_limites(self) -> None:
        random.seed(2)
        config = criar_configuracao_por_preset("Emergencia Simulada")
        for atualizacao in range(1, config.total_atualizacoes + 1):
            dado = gerar_telemetria(config, atualizacao)
            self.assertGreaterEqual(dado["temperatura_interna"], -20)
            self.assertLessEqual(dado["temperatura_interna"], 90)
            for chave in ["comunicacao_base", "bateria", "oxigenio", "estabilidade_operacional", "perda_pacotes_percentual"]:
                self.assertGreaterEqual(dado[chave], 0)
                self.assertLessEqual(dado[chave], 100)
            for chave in ["geracao_solar", "consumo_suporte_vida", "consumo_comunicacao", "consumo_estabilidade", "consumo_pesquisa", "latencia_comunicacao_ms"]:
                self.assertGreaterEqual(dado[chave], 0)

    def test_nominal_nao_comeca_critico(self) -> None:
        random.seed(3)
        config = criar_configuracao_por_preset("Orbita Terrestre")
        dado = gerar_telemetria(config, 1)
        self.assertLessEqual(calcular_pontuacao_risco(dado)["pontuacao"], 2)
        self.assertGreaterEqual(dado["comunicacao_base"], 70)

    def test_degradacao_progressiva_reduz_bateria(self) -> None:
        random.seed(4)
        config = criar_configuracao_por_preset("Ida a Lua")
        inicio = gerar_telemetria(config, 1)["bateria"]
        fim = gerar_telemetria(config, config.total_atualizacoes)["bateria"]
        self.assertLess(fim, inicio)

    def test_comunicacao_instavel_varia_sinal(self) -> None:
        random.seed(5)
        config = criar_configuracao_por_preset("Sobrevoo Lunar")
        sinais = [gerar_telemetria(config, i)["comunicacao_base"] for i in range(1, 7)]
        self.assertGreater(max(sinais) - min(sinais), 10)

    def test_perfil_critico_tem_atualizacao_critica(self) -> None:
        random.seed(6)
        config = criar_configuracao_por_preset("Emergencia Simulada")
        pontuacoes = [calcular_pontuacao_risco(gerar_telemetria(config, i))["pontuacao"] for i in range(1, config.total_atualizacoes + 1)]
        self.assertTrue(any(p >= 6 for p in pontuacoes))


if __name__ == "__main__":
    unittest.main()
