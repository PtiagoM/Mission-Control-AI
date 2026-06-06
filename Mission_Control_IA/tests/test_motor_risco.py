from __future__ import annotations

import unittest

from sistema_integrado.motor_risco import (
    analisar_bateria,
    analisar_comunicacao,
    analisar_estabilidade,
    analisar_oxigenio,
    analisar_temperatura,
    calcular_pontuacao_risco,
    gerar_recomendacoes_operacionais,
    identificar_area_mais_afetada,
)


class TestMotorRisco(unittest.TestCase):
    def test_faixas_de_risco(self) -> None:
        self.assertEqual(("NORMAL", 0), analisar_temperatura(24)[:2])
        self.assertEqual(("ATENCAO", 1), analisar_temperatura(34)[:2])
        self.assertEqual(("CRITICO", 2), analisar_temperatura(40)[:2])
        self.assertEqual(("NORMAL", 0), analisar_comunicacao(80)[:2])
        self.assertEqual(("ATENCAO", 1), analisar_comunicacao(45)[:2])
        self.assertEqual(("CRITICO", 2), analisar_comunicacao(20)[:2])
        self.assertEqual(("NORMAL", 0), analisar_bateria(80)[:2])
        self.assertEqual(("ATENCAO", 1), analisar_bateria(35)[:2])
        self.assertEqual(("CRITICO", 2), analisar_bateria(10)[:2])
        self.assertEqual(("NORMAL", 0), analisar_oxigenio(95)[:2])
        self.assertEqual(("ATENCAO", 1), analisar_oxigenio(85)[:2])
        self.assertEqual(("CRITICO", 2), analisar_oxigenio(70)[:2])
        self.assertEqual(("NORMAL", 0), analisar_estabilidade(80)[:2])
        self.assertEqual(("ATENCAO", 1), analisar_estabilidade(55)[:2])
        self.assertEqual(("CRITICO", 2), analisar_estabilidade(25)[:2])

    def test_classificacao_por_estado_atual(self) -> None:
        nominal = {"temperatura_interna": 24, "comunicacao_base": 90, "bateria": 90, "oxigenio": 96, "estabilidade_operacional": 90}
        self.assertEqual("NOMINAL", calcular_pontuacao_risco(nominal)["status"])
        atencao = {"temperatura_interna": 34, "comunicacao_base": 50, "bateria": 40, "oxigenio": 86, "estabilidade_operacional": 60}
        self.assertEqual("ATENCAO", calcular_pontuacao_risco(atencao)["status"])
        critico = {"temperatura_interna": 90, "comunicacao_base": 10, "bateria": 10, "oxigenio": 60, "estabilidade_operacional": 20}
        self.assertIn(calcular_pontuacao_risco(critico)["status"], {"CRITICO", "CONTINGENCIA"})

    def test_area_afetada_e_recomendacoes(self) -> None:
        historico = [
            calcular_pontuacao_risco({"temperatura_interna": 40, "comunicacao_base": 90, "bateria": 90, "oxigenio": 95, "estabilidade_operacional": 80}),
            calcular_pontuacao_risco({"temperatura_interna": 42, "comunicacao_base": 90, "bateria": 90, "oxigenio": 95, "estabilidade_operacional": 80}),
        ]
        area = identificar_area_mais_afetada(historico)
        self.assertEqual("Temperatura interna", area["area"])
        recs = gerar_recomendacoes_operacionais(historico[-1])
        self.assertTrue(any("Temperatura" in r for r in recs))


if __name__ == "__main__":
    unittest.main()
