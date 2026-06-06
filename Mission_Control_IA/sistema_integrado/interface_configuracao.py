from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "sistema_integrado"

from .configuracao_simulacao import (
    FONTES_DADOS,
    MODOS_IA,
    MODOS_EXECUCAO,
    PRESETS_MISSAO,
    ConfiguracaoMissao,
    calcular_total_atualizacoes,
    criar_configuracao_por_preset,
)
from .estado_missao import EstadoMissao


CORES = {
    "fundo": "#07111D",
    "painel": "#0D1726",
    "painel2": "#142235",
    "borda": "#26384F",
    "texto": "#F1F5F9",
    "muted": "#93A7C1",
    "azul": "#38BDF8",
    "verde": "#22C55E",
    "amarelo": "#F59E0B",
}


class ConfiguracaoMissaoApp(tk.Tk):
    def __init__(self, iniciar_loop: bool = True, abrir_dashboard_ao_iniciar: bool = False) -> None:
        super().__init__()
        self.title("Configuração da Missão")
        self.geometry("900x840")
        self.minsize(820, 760)
        self.configure(bg=CORES["fundo"])
        self.estado_criado: EstadoMissao | None = None
        self.abrir_dashboard_ao_iniciar = abrir_dashboard_ao_iniciar
        self.variaveis = self._criar_variaveis()
        self._configurar_estilo()
        self._montar_tela()
        self._aplicar_preset()
        if iniciar_loop:
            self.mainloop()

    def _criar_variaveis(self) -> dict[str, tk.Variable]:
        return {
            "preset": tk.StringVar(value="Orbita Terrestre"),
            "nome_missao": tk.StringVar(),
            "duracao_minutos": tk.IntVar(),
            "intervalo_monitoramento_min": tk.IntVar(),
            "escala_execucao_real_s": tk.DoubleVar(value=2.0),
            "modo_execucao": tk.StringVar(value="manual"),
            "perfil_risco": tk.StringVar(),
            "energia_inicial": tk.DoubleVar(),
            "comunicacao_inicial": tk.DoubleVar(),
            "oxigenio_inicial": tk.DoubleVar(),
            "estabilidade_inicial": tk.DoubleVar(),
            "fonte_dados": tk.StringVar(value="regras"),
            "eventos_criticos": tk.BooleanVar(value=True),
            "timeout_telemetria_ia": tk.DoubleVar(value=15.0),
            "timeout_analise_ia": tk.DoubleVar(value=25.0),
            "aquecer_modelo_ao_iniciar": tk.BooleanVar(value=False),
            "modo_ia": tk.StringVar(value="por_atualizacao"),
            "total_atualizacoes": tk.StringVar(value="Total previsto: 0 atualizações"),
        }

    def _configurar_estilo(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="#101B2B", background="#101B2B", foreground=CORES["texto"])
        style.configure("TSpinbox", fieldbackground="#101B2B", background="#101B2B", foreground=CORES["texto"])

    def _montar_tela(self) -> None:
        topo = tk.Frame(self, bg=CORES["fundo"])
        topo.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(
            topo,
            text="Configuração da Missão",
            bg=CORES["fundo"],
            fg=CORES["texto"],
            font=("Segoe UI Semibold", 24),
        ).pack(anchor="w")
        tk.Label(
            topo,
            text="Defina o cenário, a escala de tempo e as condições iniciais antes de abrir o cockpit.",
            bg=CORES["fundo"],
            fg=CORES["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        corpo = tk.Frame(self, bg=CORES["painel"], highlightbackground=CORES["borda"], highlightthickness=1)
        corpo.pack(fill="both", expand=True, padx=28, pady=16)
        corpo.columnconfigure(0, weight=1)
        corpo.columnconfigure(1, weight=1)

        self._campo_combo(corpo, "Missão predefinida", "preset", list(PRESETS_MISSAO), 0, 0)
        self._campo_texto(corpo, "Nome da missão", "nome_missao", 0, 1)
        self._campo_numero(
            corpo,
            "Duração simulada (min)",
            "duracao_minutos",
            1,
            0,
            30,
            360,
            5,
            "Tempo total da missão dentro da simulação; não representa o tempo real.",
        )
        self._campo_numero(
            corpo,
            "Intervalo de monitoramento (min)",
            "intervalo_monitoramento_min",
            1,
            1,
            1,
            60,
            1,
            "Intervalo simulado entre uma leitura operacional e outra.",
        )
        self._campo_numero(
            corpo,
            "Segundos reais por atualização",
            "escala_execucao_real_s",
            2,
            0,
            0.2,
            30,
            0.2,
            "Define a velocidade da simulação. Exemplo: 2 s por atualização.",
        )
        self._campo_combo(corpo, "Modo de execução", "modo_execucao", sorted(MODOS_EXECUCAO), 2, 1)
        self._campo_combo(
            corpo,
            "Perfil de risco",
            "perfil_risco",
            ["nominal", "degradacao_progressiva", "suporte_vida", "comunicacao_instavel", "critico"],
            3,
            0,
        )
        self._campo_combo(corpo, "Fonte dos dados", "fonte_dados", sorted(FONTES_DADOS), 3, 1, "Define se a telemetria usa regras internas ou o apoio da IA.")
        self._campo_numero(corpo, "Energia inicial (%)", "energia_inicial", 4, 0, 0, 100, 1)
        self._campo_numero(corpo, "Comunicação inicial (%)", "comunicacao_inicial", 4, 1, 0, 100, 1)
        self._campo_numero(corpo, "Oxigênio inicial (%)", "oxigenio_inicial", 5, 0, 0, 100, 1)
        self._campo_numero(corpo, "Estabilidade inicial (%)", "estabilidade_inicial", 5, 1, 0, 100, 1)
        self._campo_numero(corpo, "Timeout telemetria IA (s)", "timeout_telemetria_ia", 6, 0, 1, 60, 0.5)
        self._campo_numero(corpo, "Timeout da análise por IA (s)", "timeout_analise_ia", 6, 1, 1, 90, 0.5)
        self._campo_combo(
            corpo,
            "Modo de IA",
            "modo_ia",
            sorted(MODOS_IA),
            7,
            0,
            "Define como a IA participa. O modo por atualização pode ser mais lento.",
        )

        eventos = tk.Checkbutton(
            corpo,
            text="Eventos críticos ativados",
            variable=self.variaveis["eventos_criticos"],
            bg=CORES["painel"],
            fg=CORES["texto"],
            selectcolor=CORES["painel2"],
            activebackground=CORES["painel"],
            activeforeground=CORES["texto"],
            font=("Segoe UI", 10),
        )
        eventos.grid(row=25, column=0, sticky="w", padx=22, pady=10)

        aquecer = tk.Checkbutton(
            corpo,
            text="Aquecer modelo ao iniciar",
            variable=self.variaveis["aquecer_modelo_ao_iniciar"],
            bg=CORES["painel"],
            fg=CORES["texto"],
            selectcolor=CORES["painel2"],
            activebackground=CORES["painel"],
            activeforeground=CORES["texto"],
            font=("Segoe UI", 10),
        )
        aquecer.grid(row=25, column=1, sticky="w", padx=22, pady=10)
        tk.Label(
            corpo,
            text="Faz uma chamada inicial ao modelo local para reduzir atraso na primeira resposta da IA.",
            bg=CORES["painel"],
            fg=CORES["muted"],
            font=("Segoe UI", 8),
            wraplength=360,
            justify="left",
        ).grid(row=26, column=1, sticky="w", padx=22, pady=(0, 8))

        total = tk.Label(
            corpo,
            textvariable=self.variaveis["total_atualizacoes"],
            bg=CORES["painel"],
            fg=CORES["azul"],
            font=("Segoe UI Semibold", 12),
        )
        total.grid(row=27, column=1, sticky="e", padx=22, pady=12)

        acoes = tk.Frame(self, bg=CORES["fundo"])
        acoes.pack(fill="x", padx=28, pady=(0, 24))
        tk.Button(
            acoes,
            text="Iniciar missão",
            command=self.iniciar_missao,
            bg=CORES["azul"],
            fg="#06111F",
            activebackground="#7DD3FC",
            activeforeground="#06111F",
            font=("Segoe UI Semibold", 11),
            relief="flat",
            padx=22,
            pady=11,
        ).pack(side="right")

        for nome in [
            "duracao_minutos",
            "intervalo_monitoramento_min",
            "escala_execucao_real_s",
            "energia_inicial",
            "comunicacao_inicial",
            "oxigenio_inicial",
            "estabilidade_inicial",
            "timeout_telemetria_ia",
            "timeout_analise_ia",
        ]:
            self.variaveis[nome].trace_add("write", lambda *_args: self._atualizar_total())
        self.variaveis["preset"].trace_add("write", lambda *_args: self._aplicar_preset())

    def _rotulo(self, parent: tk.Misc, texto: str, row: int, col: int) -> None:
        tk.Label(parent, text=texto, bg=CORES["painel"], fg=CORES["muted"], font=("Segoe UI", 9)).grid(
            row=row * 3,
            column=col,
            sticky="w",
            padx=22,
            pady=(18, 4),
        )

    def _ajuda(self, parent: tk.Misc, texto: str | None, row: int, col: int) -> None:
        if not texto:
            return
        tk.Label(
            parent,
            text=texto,
            bg=CORES["painel"],
            fg=CORES["muted"],
            font=("Segoe UI", 8),
            wraplength=360,
            justify="left",
        ).grid(row=row * 3 + 2, column=col, sticky="w", padx=22, pady=(3, 0))

    def _campo_texto(self, parent: tk.Misc, label: str, chave: str, row: int, col: int, ajuda: str | None = None) -> None:
        self._rotulo(parent, label, row, col)
        tk.Entry(
            parent,
            textvariable=self.variaveis[chave],
            bg="#101B2B",
            fg=CORES["texto"],
            insertbackground=CORES["texto"],
            relief="flat",
            font=("Segoe UI", 11),
        ).grid(row=row * 3 + 1, column=col, sticky="ew", padx=22)
        self._ajuda(parent, ajuda, row, col)

    def _campo_combo(self, parent: tk.Misc, label: str, chave: str, valores: list[str], row: int, col: int, ajuda: str | None = None) -> None:
        self._rotulo(parent, label, row, col)
        ttk.Combobox(parent, textvariable=self.variaveis[chave], values=valores, state="readonly").grid(
            row=row * 3 + 1,
            column=col,
            sticky="ew",
            padx=22,
        )
        self._ajuda(parent, ajuda, row, col)

    def _campo_numero(
        self,
        parent: tk.Misc,
        label: str,
        chave: str,
        row: int,
        col: int,
        minimo: float,
        maximo: float,
        incremento: float,
        ajuda: str | None = None,
    ) -> None:
        self._rotulo(parent, label, row, col)
        ttk.Spinbox(
            parent,
            textvariable=self.variaveis[chave],
            from_=minimo,
            to=maximo,
            increment=incremento,
        ).grid(row=row * 3 + 1, column=col, sticky="ew", padx=22)
        self._ajuda(parent, ajuda, row, col)

    def _aplicar_preset(self) -> None:
        preset = PRESETS_MISSAO[self.variaveis["preset"].get()]
        self.variaveis["nome_missao"].set(preset.nome)
        self.variaveis["duracao_minutos"].set(preset.duracao_minutos)
        self.variaveis["intervalo_monitoramento_min"].set(preset.intervalo_monitoramento_min)
        self.variaveis["perfil_risco"].set(preset.perfil_risco)
        self.variaveis["energia_inicial"].set(preset.energia_inicial)
        self.variaveis["comunicacao_inicial"].set(preset.comunicacao_inicial)
        self.variaveis["oxigenio_inicial"].set(preset.oxigenio_inicial)
        self.variaveis["estabilidade_inicial"].set(preset.estabilidade_inicial)
        self.variaveis["timeout_telemetria_ia"].set(15.0)
        self.variaveis["timeout_analise_ia"].set(25.0)
        self.variaveis["modo_ia"].set("por_atualizacao")
        self._atualizar_total()

    def _atualizar_total(self) -> None:
        try:
            total = calcular_total_atualizacoes(
                int(self.variaveis["duracao_minutos"].get()),
                int(self.variaveis["intervalo_monitoramento_min"].get()),
            )
            self.variaveis["total_atualizacoes"].set(f"Total previsto: {total} atualizações")
        except (tk.TclError, ValueError):
            self.variaveis["total_atualizacoes"].set("Total previsto: ajuste a duração ou o intervalo")

    def _coletar_configuracao(self) -> ConfiguracaoMissao:
        dados: dict[str, Any] = {
            "nome_missao": str(self.variaveis["nome_missao"].get()).strip() or "Missão sem nome",
            "duracao_minutos": int(self.variaveis["duracao_minutos"].get()),
            "intervalo_monitoramento_min": int(self.variaveis["intervalo_monitoramento_min"].get()),
            "escala_execucao_real_s": float(self.variaveis["escala_execucao_real_s"].get()),
            "modo_execucao": str(self.variaveis["modo_execucao"].get()),
            "perfil_risco": str(self.variaveis["perfil_risco"].get()),
            "energia_inicial": float(self.variaveis["energia_inicial"].get()),
            "comunicacao_inicial": float(self.variaveis["comunicacao_inicial"].get()),
            "oxigenio_inicial": float(self.variaveis["oxigenio_inicial"].get()),
            "estabilidade_inicial": float(self.variaveis["estabilidade_inicial"].get()),
            "fonte_dados": str(self.variaveis["fonte_dados"].get()),
            "eventos_criticos": bool(self.variaveis["eventos_criticos"].get()),
            "timeout_telemetria_ia": float(self.variaveis["timeout_telemetria_ia"].get()),
            "timeout_analise_ia": float(self.variaveis["timeout_analise_ia"].get()),
            "aquecer_modelo_ao_iniciar": bool(self.variaveis["aquecer_modelo_ao_iniciar"].get()),
            "modo_ia": str(self.variaveis["modo_ia"].get()),
        }
        return ConfiguracaoMissao(**dados)

    def criar_estado_missao(self) -> EstadoMissao:
        config = self._coletar_configuracao()
        self.estado_criado = EstadoMissao(config)
        self.estado_criado.iniciar_simulacao()
        return self.estado_criado

    def iniciar_missao(self) -> None:
        try:
            estado = self.criar_estado_missao()
        except (ValueError, tk.TclError) as erro:
            messagebox.showerror("Configuração inválida", str(erro))
            return
        if self.abrir_dashboard_ao_iniciar:
            self.destroy()
            from .interface_principal import DashboardMissaoApp

            DashboardMissaoApp(estado, iniciar_loop=True)


def main() -> None:
    ConfiguracaoMissaoApp(iniciar_loop=True, abrir_dashboard_ao_iniciar=True)


if __name__ == "__main__":
    main()
