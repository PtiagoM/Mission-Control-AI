from __future__ import annotations

import unittest

from sistema_integrado.motor_eventos import MotorEventos


class TestMotorEventos(unittest.TestCase):
    def test_eventos_e_filtros(self) -> None:
        motor = MotorEventos()
        inicio = motor.registrar_info(0, 0, "Missao iniciada")
        critico = motor.registrar_evento(1, 5, "CRITICO", "Sistema de energia", "Bateria critica", "Bateria abaixo de 20%", "Reduzir cargas nao essenciais")
        self.assertEqual(1, inicio["id"])
        self.assertEqual(2, critico["id"])
        self.assertFalse(critico["reconhecido"])
        self.assertEqual(1, len(motor.filtrar("CRITICO")))
        motor.reconhecer_evento(critico["id"])
        self.assertTrue(motor.eventos[-1]["reconhecido"])
        motor.reconhecer_todos()
        self.assertTrue(all(e["reconhecido"] for e in motor.eventos))


if __name__ == "__main__":
    unittest.main()
