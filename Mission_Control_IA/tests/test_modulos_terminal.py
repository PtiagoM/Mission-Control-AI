from __future__ import annotations

import subprocess
import sys
import unittest


class TestModulosTerminal(unittest.TestCase):
    def run_module(self, filename: str, stdin: str = "") -> str:
        result = subprocess.run(
            [sys.executable, filename],
            input=stdin,
            text=True,
            capture_output=True,
            timeout=12,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        return result.stdout

    def test_core_executa(self) -> None:
        out = self.run_module("entregas_materias/automacao_python/mission_control_core.py")
        self.assertIn("MISSION CONTROL AI", out)
        self.assertIn("Risco", out)
        self.assertIn("RELAT", out)

    def test_dsa_terminal_executa_fluxo_minimo(self) -> None:
        out = self.run_module("entregas_materias/dsa/dsa_terminal.py", "5\n3\n4\n0\n")
        self.assertIn("Alerta de superaquecimento", out)
        self.assertIn("Ativar economia de energia", out)
        self.assertIn("Falha de comunicacao", out)

    def test_energy_monitor_executa(self) -> None:
        out = self.run_module("entregas_materias/energias_sustentaveis/energy_monitor.py")
        self.assertIn("Gera", out)
        self.assertIn("Consumo", out)
        self.assertIn("Saldo", out)
        self.assertIn("autonomia", out.lower())


if __name__ == "__main__":
    unittest.main()
