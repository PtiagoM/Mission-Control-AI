from __future__ import annotations

import unittest
import importlib
import os
from unittest.mock import patch

from sistema_integrado.assistente_ia import (
    MODELO_PADRAO_OLLAMA,
    TIMEOUT_ANALISE_IA,
    TIMEOUT_RELATORIO_IA,
    TIMEOUT_STATUS_OLLAMA,
    TIMEOUT_TELEMETRIA_IA,
    aquecer_modelo_ollama,
    analisar_com_fallback,
    analisar_missao_com_ia,
    diagnosticar_geracao_telemetria_ia,
    gerar_telemetria_ia_com_fallback,
    consultar_modelo_local,
    validar_telemetria_ia,
)
from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao


class TestAssistenteIA(unittest.TestCase):
    def test_json_valido_e_aceito(self) -> None:
        texto = '{"temperatura_interna": 30, "comunicacao_base": 80, "bateria": 70, "oxigenio": 95, "estabilidade_operacional": 85, "geracao_solar": 500, "consumo_suporte_vida": 170, "consumo_comunicacao": 90, "consumo_estabilidade": 110, "consumo_pesquisa": 95, "latencia_comunicacao_ms": 200, "perda_pacotes_percentual": 2}'
        dado = validar_telemetria_ia(texto)
        self.assertTrue(dado["valido"])
        self.assertEqual(70, dado["telemetria"]["bateria"])

    def test_texto_solto_rejeitado(self) -> None:
        dado = validar_telemetria_ia("temperatura alta e energia baixa")
        self.assertFalse(dado["valido"])

    def test_valores_invalidos_sao_corrigidos(self) -> None:
        texto = '{"temperatura_interna": 200, "comunicacao_base": 80, "bateria": 140, "oxigenio": -10, "estabilidade_operacional": 85, "geracao_solar": -1, "consumo_suporte_vida": 170, "consumo_comunicacao": 90, "consumo_estabilidade": 110, "consumo_pesquisa": 95, "latencia_comunicacao_ms": -5, "perda_pacotes_percentual": 300}'
        dado = validar_telemetria_ia(texto)
        self.assertTrue(dado["valido"])
        self.assertEqual(90, dado["telemetria"]["temperatura_interna"])
        self.assertEqual(100, dado["telemetria"]["bateria"])
        self.assertEqual(0, dado["telemetria"]["oxigenio"])

    def test_funciona_com_ia_desligada(self) -> None:
        resposta = analisar_com_fallback({"status_geral": "ATENCAO"}, usar_ia=False)
        self.assertIn("modo deterministico", resposta["origem"])
        self.assertIn("recomendacao", resposta)

    def test_modelo_padrao_ollama(self) -> None:
        self.assertEqual("llama3.2:1b", MODELO_PADRAO_OLLAMA)

    def test_timeouts_configuraveis_padrao(self) -> None:
        self.assertEqual(1.5, TIMEOUT_STATUS_OLLAMA)
        self.assertGreaterEqual(TIMEOUT_TELEMETRIA_IA, 8.0)
        self.assertGreaterEqual(TIMEOUT_ANALISE_IA, 12.0)
        self.assertGreaterEqual(TIMEOUT_RELATORIO_IA, 20.0)

    def test_validador_aceita_json_aninhado_e_lista(self) -> None:
        base = '{"temperatura_interna": "30", "comunicacao_base": "80", "bateria": "70", "oxigenio": "95", "estabilidade_operacional": "85", "geracao_solar": "500", "consumo_suporte_vida": "170", "consumo_comunicacao": "90", "consumo_estabilidade": "110", "consumo_pesquisa": "95", "latencia_comunicacao_ms": "200", "perda_pacotes_percentual": "2"}'
        self.assertTrue(validar_telemetria_ia(f'{{"telemetria": {base}}}')["valido"])
        self.assertTrue(validar_telemetria_ia(f'[{base}]')["valido"])

    def test_validador_informa_chaves_faltantes(self) -> None:
        dado = validar_telemetria_ia('{"temperatura_interna": 30}')
        self.assertFalse(dado["valido"])
        self.assertIn("bateria", dado["chaves_faltantes"])
        self.assertIn("temperatura_interna", dado["chaves_recebidas"])

    def test_modelo_respeita_variavel_de_ambiente(self) -> None:
        import sistema_integrado.assistente_ia as modulo_ia

        original = os.environ.get("MISSION_CONTROL_IA_MODELO")
        try:
            os.environ["MISSION_CONTROL_IA_MODELO"] = "modelo-teste"
            recarregado = importlib.reload(modulo_ia)
            self.assertEqual("modelo-teste", recarregado.MODELO_PADRAO_OLLAMA)
        finally:
            if original is None:
                os.environ.pop("MISSION_CONTROL_IA_MODELO", None)
            else:
                os.environ["MISSION_CONTROL_IA_MODELO"] = original
            importlib.reload(modulo_ia)

    @patch("sistema_integrado.assistente_ia.consultar_modelo_local")
    def test_telemetria_ia_retorna_origem_correta(self, mock_consulta) -> None:
        texto = '{"temperatura_interna": 30, "comunicacao_base": 80, "bateria": 70, "oxigenio": 95, "estabilidade_operacional": 85, "geracao_solar": 500, "consumo_suporte_vida": 170, "consumo_comunicacao": 90, "consumo_estabilidade": 110, "consumo_pesquisa": 95, "latencia_comunicacao_ms": 200, "perda_pacotes_percentual": 2}'
        mock_consulta.return_value = {"ok": True, "motivo": "ok", "texto": texto}
        config = criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras")
        resultado = gerar_telemetria_ia_com_fallback(config, 1, {"temperatura_interna": 20})
        self.assertEqual("ia + regras", resultado["origem"])
        self.assertEqual("", resultado["erro_tecnico"])
        self.assertIn("diagnostico", resultado)
        self.assertIn("prompt", resultado["diagnostico"])

    @patch("sistema_integrado.assistente_ia.consultar_modelo_local")
    def test_diagnostico_telemetria_mostra_chaves_faltantes(self, mock_consulta) -> None:
        mock_consulta.return_value = {"ok": True, "motivo": "ok", "texto": '{"temperatura_interna": 30}', "tempo_resposta_s": 0.2, "timeout_usado": 12.0}
        config = criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras")
        diagnostico = diagnosticar_geracao_telemetria_ia(config, 1, {"temperatura_interna": 20})
        self.assertFalse(diagnostico["validacao_ok"])
        self.assertIn("bateria", diagnostico["chaves_faltantes"])
        self.assertEqual("fallback deterministico", diagnostico["origem_final"])

    @patch("sistema_integrado.assistente_ia.consultar_modelo_local")
    def test_analise_missao_usa_ia_quando_modelo_responde(self, mock_consulta) -> None:
        mock_consulta.return_value = {
            "ok": True,
            "motivo": "ok",
            "texto": '{"resumo": "Missao em monitoramento.", "principal_risco": "Sistema de energia.", "justificativa": "Bateria exige acompanhamento.", "prioridade_operacional": "Energia", "proxima_acao": "Reduzir cargas secundarias.", "nivel_confianca": "alto", "observacao": "Analise baseada nos dados enviados."}',
        }
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        resposta = analisar_missao_com_ia(estado, usar_ia=True)
        self.assertEqual("IA", resposta["origem"])
        self.assertEqual("nao", resposta["fallback_usado"])
        self.assertIn("prompt", resposta)

    @patch("sistema_integrado.assistente_ia.consultar_modelo_local")
    def test_analise_missao_fallback_quando_modelo_falha(self, mock_consulta) -> None:
        mock_consulta.return_value = {"ok": False, "motivo": "Ollama offline.", "texto": ""}
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        resposta = analisar_missao_com_ia(estado, usar_ia=True)
        self.assertIn("fallback", resposta["origem"])
        self.assertEqual("sim", resposta["fallback_usado"])

    @patch("sistema_integrado.assistente_ia.consultar_modelo_local")
    def test_aquecer_modelo_nao_quebra(self, mock_consulta) -> None:
        mock_consulta.return_value = {"ok": True, "motivo": "ok", "texto": '{"ok": true}'}
        resultado = aquecer_modelo_ollama()
        self.assertTrue(resultado["ok"])


if __name__ == "__main__":
    unittest.main()
