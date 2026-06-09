from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[1]


class TestEstruturaProjeto(unittest.TestCase):
    def test_pastas_principais_existentes(self) -> None:
        self.assertTrue((RAIZ / "main.py").is_file())
        self.assertTrue((RAIZ / "README.md").is_file())
        self.assertTrue((RAIZ / "sistema_integrado").is_dir())
        self.assertTrue((RAIZ / "entregas_materias").is_dir())
        self.assertTrue((RAIZ / "tests").is_dir())

    def test_benchmark_e_diagnostico_ficam_em_tests(self) -> None:
        self.assertTrue((RAIZ / "tests" / "benchmark_ia.py").is_file())
        self.assertTrue((RAIZ / "tests" / "diagnostico_ia.py").is_file())
        self.assertFalse((RAIZ / "benchmark_ia.py").exists())
        self.assertFalse((RAIZ / "diagnostico_ia.py").exists())

    def test_main_abre_configuracao_da_missao(self) -> None:
        main = importlib.import_module("main")
        with patch("sistema_integrado.interface_configuracao.main") as mock_config:
            main.main()
        mock_config.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
