from __future__ import annotations

"""Entrada principal do Mission Control AI.

O sistema sempre inicia pela configuração da missão para garantir que o
dashboard receba um EstadoMissao já inicializado com os parâmetros escolhidos.
"""

from sistema_integrado import interface_configuracao


def main() -> None:
    interface_configuracao.main()


if __name__ == "__main__":
    main()
