from __future__ import annotations

import unittest

from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao


class TestEstadoMissao(unittest.TestCase):
    def test_inicio_e_avanco(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        self.assertEqual(0, estado.atualizacao_atual)
        self.assertEqual(0, estado.tempo_decorrido_min)
        self.assertTrue(estado.missao_em_execucao)
        self.assertFalse(estado.missao_finalizada)
        self.assertEqual(1, len(estado.historico_eventos))
        estado.avancar_atualizacao()
        self.assertEqual(1, estado.atualizacao_atual)
        self.assertEqual(estado.configuracao.intervalo_monitoramento_min, estado.tempo_decorrido_min)
        self.assertEqual(1, len(estado.historico_telemetria))
        self.assertEqual(1, len(estado.historico_energia))

    def test_finalizacao_e_limite(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Emergencia Simulada"))
        estado.iniciar_simulacao()
        for _ in range(estado.total_atualizacoes):
            estado.avancar_atualizacao()
        self.assertTrue(estado.missao_finalizada)
        total = len(estado.historico_telemetria)
        estado.avancar_atualizacao()
        self.assertEqual(total, len(estado.historico_telemetria))

    def test_pausar_e_reiniciar(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        estado.pausar_simulacao()
        self.assertTrue(estado.missao_pausada)
        estado.reiniciar_simulacao()
        self.assertEqual(0, estado.atualizacao_atual)
        self.assertFalse(estado.historico_telemetria)


if __name__ == "__main__":
    unittest.main()
