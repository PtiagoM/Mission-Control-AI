from __future__ import annotations

import unittest
from unittest.mock import patch

from sistema_integrado.configuracao_simulacao import criar_configuracao_por_preset
from sistema_integrado.estado_missao import EstadoMissao
from sistema_integrado.interface_configuracao import ConfiguracaoMissaoApp
from sistema_integrado.interface_principal import DashboardMissaoApp


class TestInterface(unittest.TestCase):
    def test_configuracao_instancia_e_gera_estado(self) -> None:
        app = ConfiguracaoMissaoApp(iniciar_loop=False)
        estado = app.criar_estado_missao()
        self.assertIsInstance(estado, EstadoMissao)
        app.destroy()

    def test_dashboard_instancia_e_atualiza_por_fluxo_central(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        with patch.object(app, "atualizar_interface_completa", wraps=app.atualizar_interface_completa) as mock_atualizar:
            app.avancar_atualizacao()
            self.assertTrue(mock_atualizar.called)
        app.atualizar_cards()
        app.atualizar_graficos()
        app.atualizar_alertas()
        self.assertEqual(estado.atualizacao_atual, app.dados_interface_cache["atualizacao_atual"])
        self.assertEqual(len(estado.historico_telemetria), len(app.dados_interface_cache["telemetria"]))
        app.destroy()

    def test_dashboard_prepara_dados_de_todas_as_secoes_ao_avancar(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        app.avancar_atualizacao()
        cache = app.dados_interface_cache
        for chave in ["cockpit", "telemetria", "energia", "comunicacao", "eventos", "ia", "historico", "graficos"]:
            self.assertIn(chave, cache)
        self.assertEqual(1, cache["atualizacao_atual"])
        self.assertEqual(1, len(cache["historico"]))
        self.assertEqual(1, len(cache["graficos"]["risco"]))
        app.destroy()

    def test_comunicacao_tem_linha_operacional_ou_mensagem_vazia(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        app._abrir_secao("Comunicação")
        tabela = app.tabelas["eventos_comunicacao"]
        linhas = tabela.get_children()
        self.assertGreaterEqual(len(linhas), 1)
        valores = tabela.item(linhas[0], "values")
        self.assertEqual(5, len(valores))
        self.assertTrue(valores[2])
        app.destroy()

    def test_ia_usa_tres_paineis_separados(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre", fonte_dados="ia_regras"))
        estado.iniciar_simulacao()
        estado.avancar_atualizacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        app._abrir_secao("AI Mission Advisor")
        self.assertIn("ia_terminal", app.cards)
        self.assertIn("ia_prompt", app.cards)
        self.assertIn("ia_analise", app.cards)
        self.assertNotIn("ia_status", app.cards)
        self.assertNotIn("ia_json", app.cards)
        self.assertIn("Prompt", app.cards["ia_prompt"].get("1.0", "end"))
        app.destroy()

    def test_historico_nao_repete_botoes_de_simulacao(self) -> None:
        estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
        estado.iniciar_simulacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        app._abrir_secao("Histórico / Simulação")
        self.assertEqual([], app.botoes_controle)
        self.assertIn("historico_bruto", app.tabelas)
        app.destroy()

    def test_modo_automatico_agenda_primeira_atualizacao(self) -> None:
        config = criar_configuracao_por_preset(
            "Orbita Terrestre",
            nome_missao="Teste automatico",
            duracao_minutos=10,
            intervalo_monitoramento_min=5,
            escala_execucao_real_s=0.2,
            modo_execucao="automatico",
        )
        estado = EstadoMissao(config)
        estado.iniciar_simulacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        self.assertIsNotNone(app._after_id)
        app._tick_automatico()
        self.assertEqual(1, estado.atualizacao_atual)
        app.destroy()

    def test_executar_ate_o_fim_com_ia_encadeia_ciclos_individuais(self) -> None:
        estado = EstadoMissao(
            criar_configuracao_por_preset(
                "Orbita Terrestre",
                fonte_dados="ia_regras",
                duracao_minutos=10,
                intervalo_monitoramento_min=5,
            )
        )
        estado.iniciar_simulacao()
        app = DashboardMissaoApp(estado, iniciar_loop=False)
        with patch.object(app, "_avancar_atualizacao_async") as mock_avancar, patch.object(
            estado, "executar_ate_o_fim"
        ) as mock_execucao_bloqueante:
            app.executar_ate_o_fim()
        mock_avancar.assert_called_once_with(ao_finalizar=app._continuar_execucao_ia)
        mock_execucao_bloqueante.assert_not_called()
        app.destroy()


if __name__ == "__main__":
    unittest.main()
