from __future__ import annotations

import unittest

from sistema_integrado.motor_energia import analisar_energia, calcular_autonomia, calcular_consumo_total, calcular_saldo_energia


class TestMotorEnergia(unittest.TestCase):
    def test_calculos_basicos(self) -> None:
        telemetria = {
            "bateria": 50,
            "geracao_solar": 500,
            "consumo_suporte_vida": 170,
            "consumo_comunicacao": 90,
            "consumo_estabilidade": 110,
            "consumo_pesquisa": 80,
        }
        self.assertEqual(450, calcular_consumo_total(telemetria))
        self.assertEqual(50, calcular_saldo_energia(telemetria))
        self.assertAlmostEqual((5000 * 0.5) / 450, calcular_autonomia(telemetria), places=3)

    def test_classificacoes(self) -> None:
        normal = analisar_energia({"bateria": 80, "geracao_solar": 600, "consumo_suporte_vida": 100, "consumo_comunicacao": 100, "consumo_estabilidade": 100, "consumo_pesquisa": 100})
        self.assertEqual("NORMAL", normal["status"])
        self.assertEqual("OPERACAO NOMINAL", normal["modo_energetico"])
        atencao = analisar_energia({"bateria": 45, "geracao_solar": 300, "consumo_suporte_vida": 100, "consumo_comunicacao": 100, "consumo_estabilidade": 100, "consumo_pesquisa": 100})
        self.assertEqual("ATENCAO", atencao["status"])
        self.assertEqual("CONSERVACAO", atencao["modo_energetico"])
        critico = analisar_energia({"bateria": 15, "geracao_solar": 100, "consumo_suporte_vida": 100, "consumo_comunicacao": 100, "consumo_estabilidade": 100, "consumo_pesquisa": 100})
        self.assertEqual("CRITICO", critico["status"])
        self.assertEqual("EMERGENCIA", critico["modo_energetico"])
        self.assertTrue(any("não essenciais" in r for r in critico["recomendacoes"]))


if __name__ == "__main__":
    unittest.main()
