from __future__ import annotations

import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
ARQUIVOS_VISIVEIS = [
    RAIZ / "main.py",
    RAIZ / "sistema_integrado" / "interface_configuracao.py",
    RAIZ / "sistema_integrado" / "interface_principal.py",
    RAIZ / "sistema_integrado" / "relatorio_missao.py",
]


class TestTextosPtBr(unittest.TestCase):
    def test_interfaces_nao_possuem_texto_com_codificacao_corrompida(self) -> None:
        for arquivo in ARQUIVOS_VISIVEIS:
            texto = arquivo.read_text(encoding="utf-8")
            for trecho_corrompido in ["Ã§", "Ã£", "Ã©", "Ãª", "Ã³", "Ãº", "Ã­", "Â°", "Â"]:
                self.assertNotIn(trecho_corrompido, texto, msg=str(arquivo))

    def test_rotulos_principais_usam_acentuacao_ptbr(self) -> None:
        configuracao = (RAIZ / "sistema_integrado" / "interface_configuracao.py").read_text(encoding="utf-8")
        interface = (RAIZ / "sistema_integrado" / "interface_principal.py").read_text(encoding="utf-8")
        for trecho in ["Configuração da Missão", "Iniciar missão", "Duração simulada", "Comunicação inicial"]:
            self.assertIn(trecho, configuracao)
        for trecho in ["Atualização", "Comunicação", "Histórico / Simulação", "Análise"]:
            self.assertIn(trecho, interface)


if __name__ == "__main__":
    unittest.main()
