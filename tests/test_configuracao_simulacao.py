from __future__ import annotations

import unittest

from sistema_integrado.configuracao_simulacao import (
    MODOS_IA,
    MODOS_EXECUCAO,
    PRESETS_MISSAO,
    ConfiguracaoMissao,
    calcular_total_atualizacoes,
    criar_configuracao_por_preset,
)


class TestConfiguracaoSimulacao(unittest.TestCase):
    def test_presets_obrigatorios_existem(self) -> None:
        esperados = {"Ida a Lua", "Orbita Terrestre", "Operacao de Capsula", "Sobrevoo Lunar", "Emergencia Simulada"}
        self.assertEqual(esperados, set(PRESETS_MISSAO))

    def test_presets_possuem_campos_minimos(self) -> None:
        for preset in PRESETS_MISSAO.values():
            self.assertGreater(preset.duracao_minutos, 0)
            self.assertGreater(preset.intervalo_monitoramento_min, 0)
            self.assertIn(preset.perfil_risco, {"nominal", "degradacao_progressiva", "suporte_vida", "comunicacao_instavel", "critico"})
            self.assertGreaterEqual(preset.energia_inicial, 0)
            self.assertGreaterEqual(preset.comunicacao_inicial, 0)
            self.assertGreaterEqual(preset.oxigenio_inicial, 0)
            self.assertGreaterEqual(preset.estabilidade_inicial, 0)

    def test_calculo_total_atualizacoes(self) -> None:
        self.assertEqual(18, calcular_total_atualizacoes(90, 5))

    def test_configuracao_rejeita_intervalo_invalido(self) -> None:
        with self.assertRaises(ValueError):
            ConfiguracaoMissao("Teste", 90, 0, 1, "manual", "nominal", 80, 80, 90, 90)

    def test_configuracao_rejeita_duracao_menor_que_intervalo(self) -> None:
        with self.assertRaises(ValueError):
            ConfiguracaoMissao("Teste", 5, 10, 1, "manual", "nominal", 80, 80, 90, 90)

    def test_escala_real_deve_ser_positiva(self) -> None:
        with self.assertRaises(ValueError):
            ConfiguracaoMissao("Teste", 90, 5, 0, "manual", "nominal", 80, 80, 90, 90)

    def test_modo_execucao_valido(self) -> None:
        self.assertEqual({"manual", "automatico"}, MODOS_EXECUCAO)
        with self.assertRaises(ValueError):
            ConfiguracaoMissao("Teste", 90, 5, 1, "lento", "nominal", 80, 80, 90, 90)

    def test_configuracao_ia_valida(self) -> None:
        self.assertEqual({"por_atualizacao", "pre_geracao_futura_desativada"}, MODOS_IA)
        config = criar_configuracao_por_preset("Orbita Terrestre")
        self.assertEqual(60.0, config.timeout_telemetria_ia)
        self.assertEqual(60.0, config.timeout_analise_ia)
        self.assertEqual("por_atualizacao", config.modo_ia)
        with self.assertRaises(ValueError):
            criar_configuracao_por_preset("Orbita Terrestre", timeout_telemetria_ia=0)

    def test_criar_configuracao_por_preset(self) -> None:
        config = criar_configuracao_por_preset("Orbita Terrestre")
        self.assertEqual(18, config.total_atualizacoes)
        self.assertEqual("nominal", config.perfil_risco)


if __name__ == "__main__":
    unittest.main()
