from __future__ import annotations

import sys
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "sistema_integrado"

from .assistente_ia import MODELO_PADRAO_OLLAMA, modelo_esta_disponivel, verificar_status_ollama
from .configuracao_simulacao import criar_configuracao_por_preset
from .estado_missao import EstadoMissao
from .relatorio_missao import formatar_relatorio_texto, gerar_relatorio


"""Dashboard principal do Mission Control AI.

A interface é montada em seções, mas cada ciclo da missão prepara um cache
central com os dados de todas elas. Assim a troca de tela nunca mostra dados
antigos e o modo automático usa o mesmo fluxo visual do modo manual.
"""

CORES = {
    "fundo": "#050A12",
    "nav": "#07111D",
    "painel": "#0D1726",
    "painel2": "#142235",
    "painel3": "#192A40",
    "borda": "#26384F",
    "texto": "#F1F5F9",
    "muted": "#93A7C1",
    "azul": "#38BDF8",
    "verde": "#22C55E",
    "amarelo": "#F59E0B",
    "vermelho": "#EF4444",
    "violeta": "#A78BFA",
    "cinza": "#64748B",
}

STATUS_CORES = {
    "NOMINAL": CORES["verde"],
    "NORMAL": CORES["verde"],
    "ESTAVEL": CORES["verde"],
    "ATENCAO": CORES["amarelo"],
    "CRITICO": CORES["vermelho"],
    "CONTINGENCIA": CORES["vermelho"],
    "FINALIZADA": CORES["azul"],
    "SEM DADOS": CORES["muted"],
    "INFO": CORES["azul"],
    "IA": CORES["azul"],
    "CONSERVACAO": CORES["amarelo"],
    "EMERGENCIA": CORES["vermelho"],
    "OPERACAO NOMINAL": CORES["verde"],
}

STATUS_ROTULOS = {
    "ATENCAO": "ATENÇÃO",
    "CRITICO": "CRÍTICO",
    "ESTAVEL": "ESTÁVEL",
    "CONSERVACAO": "CONSERVAÇÃO",
    "EMERGENCIA": "EMERGÊNCIA",
    "OPERACAO NOMINAL": "OPERAÇÃO NOMINAL",
    "CONTINGENCIA": "CONTINGÊNCIA",
    "SEM DADOS": "SEM DADOS",
}


def formatar_status(status: str) -> str:
    return STATUS_ROTULOS.get(status, status)


def normalizar_status_visual(status: Any) -> str:
    return formatar_status(str(status))


def cor_por_status(status: Any) -> str:
    return STATUS_CORES.get(str(status).upper(), STATUS_CORES.get(str(status), CORES["texto"]))


def status_por_valor(valor: float, bom_minimo: float, atencao_minimo: float) -> str:
    if valor >= bom_minimo:
        return "NOMINAL"
    if valor >= atencao_minimo:
        return "ATENCAO"
    return "CRITICO"


def status_temperatura(valor: float) -> str:
    if valor < 18 or valor > 38:
        return "CRITICO"
    if valor < 20 or valor > 30:
        return "ATENCAO"
    return "NOMINAL"


def status_saldo(valor: float) -> str:
    if valor >= 0:
        return "NOMINAL"
    if valor >= -80:
        return "ATENCAO"
    return "CRITICO"


def grafico_cor_padrao(chave: str) -> str:
    return {
        "geracao_solar": CORES["verde"],
        "consumo_total": CORES["amarelo"],
        "autonomia": CORES["azul"],
        "estabilidade": CORES["violeta"],
    }.get(chave, CORES["azul"])


class GraficoLinha(tk.Canvas):
    def __init__(self, parent: tk.Misc, titulo: str, cor: str = CORES["azul"], altura: int = 150) -> None:
        super().__init__(
            parent,
            height=altura,
            bg=CORES["painel"],
            highlightthickness=1,
            highlightbackground=CORES["borda"],
        )
        self.titulo = titulo
        self.cor = cor
        self.bind("<Configure>", lambda _evento: self.redesenhar())
        self.series: list[float] = []

    def set_dados(self, series: list[float]) -> None:
        self.series = series
        self.redesenhar()

    def redesenhar(self) -> None:
        self.delete("all")
        largura = max(120, self.winfo_width())
        altura = max(90, self.winfo_height())
        margem = 28
        self.create_text(12, 12, text=self.titulo, fill=CORES["texto"], anchor="nw", font=("Segoe UI Semibold", 9))
        self.create_line(margem, altura - margem, largura - 12, altura - margem, fill=CORES["borda"])
        self.create_line(margem, 34, margem, altura - margem, fill=CORES["borda"])
        if not self.series:
            self.create_text(largura / 2, altura / 2, text="Aguardando dados", fill=CORES["muted"], font=("Segoe UI", 9))
            return
        minimo = min(self.series)
        maximo = max(self.series)
        if minimo == maximo:
            minimo -= 1
            maximo += 1
        pontos: list[float] = []
        for indice, valor in enumerate(self.series):
            x = margem + (largura - margem - 16) * (indice / max(1, len(self.series) - 1))
            y = altura - margem - ((valor - minimo) / (maximo - minimo)) * (altura - margem - 42)
            pontos.extend([x, y])
        if len(pontos) >= 4:
            self.create_line(*pontos, fill=self.cor, width=2, smooth=True)
        for x, y in zip(pontos[::2], pontos[1::2]):
            self.create_oval(x - 3, y - 3, x + 3, y + 3, fill=self.cor, outline="")
        self.create_text(largura - 14, 12, text=f"{self.series[-1]:.1f}", fill=self.cor, anchor="ne", font=("Segoe UI Semibold", 11))


class DashboardMissaoApp(tk.Tk):
    secoes = [
        "Cockpit Geral",
        "Telemetria",
        "Energia Sustentável",
        "Comunicação",
        "Alertas e Eventos",
        "AI Mission Advisor",
        "Relatório",
        "Histórico / Simulação",
    ]

    def __init__(self, estado: EstadoMissao, iniciar_loop: bool = True) -> None:
        super().__init__()
        self.estado = estado
        self.title("Mission Control AI")
        self.geometry("1440x900")
        self.minsize(1180, 740)
        self.configure(bg=CORES["fundo"])
        self.secao_ativa = "Cockpit Geral"
        self._after_id: str | None = None
        self.nav_botoes: dict[str, tk.Label] = {}
        self.cards: dict[str, tk.Label] = {}
        self.card_paineis: dict[str, tk.Frame] = {}
        self.paineis_texto: dict[str, tk.Frame] = {}
        self.graficos: dict[str, GraficoLinha] = {}
        self.tabelas: dict[str, ttk.Treeview] = {}
        self.botoes_controle: list[tk.Button] = []
        self.operacao_ia_var = tk.StringVar(value="")
        self._ia_em_execucao = False
        self._execucao_continua_ia = False
        self._analise_em_execucao = False
        self._relatorio_em_execucao = False
        self._ultimo_relatorio_texto = ""
        self.dados_interface_cache: dict[str, Any] = {}
        self.terminal_ia_linhas: list[str] = []
        self.filtro_eventos = tk.StringVar(value="Todos")
        self.status_var = tk.StringVar(value=self.estado.status_geral)
        self._configurar_estilo()
        self._montar_layout()
        self._abrir_secao("Cockpit Geral")
        self.atualizar_interface_completa()
        if self.estado.configuracao.fonte_dados == "ia_regras" and self.estado.configuracao.aquecer_modelo_ao_iniciar:
            self._aquecer_modelo_async()
        if self.estado.configuracao.modo_execucao == "automatico":
            self._agendar_automatico()
        if iniciar_loop:
            self.mainloop()

    def _configurar_estilo(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Dark.Treeview",
            background=CORES["painel"],
            foreground=CORES["texto"],
            fieldbackground=CORES["painel"],
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=CORES["painel2"],
            foreground=CORES["muted"],
            borderwidth=0,
            font=("Segoe UI Semibold", 9),
        )
        style.map("Dark.Treeview", background=[("selected", CORES["painel3"])])

    def _montar_layout(self) -> None:
        self.nav = tk.Frame(self, bg=CORES["nav"], width=230)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        tk.Label(
            self.nav,
            text="Mission\nControl AI",
            bg=CORES["nav"],
            fg=CORES["texto"],
            justify="left",
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w", padx=22, pady=(24, 18))
        for secao in self.secoes:
            item = tk.Label(
                self.nav,
                text=secao,
                bg=CORES["nav"],
                fg=CORES["muted"],
                anchor="w",
                padx=16,
                pady=10,
                font=("Segoe UI Semibold", 10),
                cursor="hand2",
            )
            item.pack(fill="x", padx=12, pady=2)
            item.bind("<Button-1>", lambda _evento, nome=secao: self._abrir_secao(nome))
            self.nav_botoes[secao] = item

        self.area = tk.Frame(self, bg=CORES["fundo"])
        self.area.pack(side="left", fill="both", expand=True)

        self.topo = tk.Frame(self.area, bg=CORES["fundo"])
        self.topo.pack(fill="x", padx=24, pady=(20, 10))
        self.titulo_secao = tk.Label(
            self.topo,
            text="Cockpit Geral",
            bg=CORES["fundo"],
            fg=CORES["texto"],
            font=("Segoe UI Semibold", 22),
        )
        self.titulo_secao.pack(side="left")
        self.resumo_topo = tk.Label(
            self.topo,
            text="",
            bg=CORES["fundo"],
            fg=CORES["muted"],
            font=("Segoe UI", 10),
        )
        self.resumo_topo.pack(side="right")

        self.conteudo = tk.Frame(self.area, bg=CORES["fundo"])
        self.conteudo.pack(fill="both", expand=True, padx=24, pady=(0, 16))

    def _abrir_secao(self, secao: str) -> None:
        self.secao_ativa = secao
        self.titulo_secao.configure(text=secao)
        for nome, botao in self.nav_botoes.items():
            botao.configure(bg=CORES["painel2"] if nome == secao else CORES["nav"], fg=CORES["texto"] if nome == secao else CORES["muted"])
        for widget in self.conteudo.winfo_children():
            widget.destroy()
        self.cards.clear()
        self.card_paineis.clear()
        self.paineis_texto.clear()
        self.graficos.clear()
        self.tabelas.clear()
        self.botoes_controle.clear()
        construtores = {
            "Cockpit Geral": self._montar_cockpit,
            "Telemetria": self._montar_telemetria,
            "Energia Sustentável": self._montar_energia,
            "Comunicação": self._montar_comunicacao,
            "Alertas e Eventos": self._montar_eventos,
            "AI Mission Advisor": self._montar_ia,
            "Relatório": self._montar_relatorio,
            "Histórico / Simulação": self._montar_historico,
        }
        construtores[secao]()
        self.atualizar_interface_completa()

    def _frame_grade(self, colunas: int) -> tk.Frame:
        frame = tk.Frame(self.conteudo, bg=CORES["fundo"])
        frame.pack(fill="both", expand=True)
        for coluna in range(colunas):
            frame.columnconfigure(coluna, weight=1, uniform="col")
        return frame

    def _configurar_linhas(self, frame: tk.Frame, pesos: dict[int, int]) -> None:
        for linha, peso in pesos.items():
            frame.rowconfigure(linha, weight=peso)

    def _painel(self, parent: tk.Misc, row: int, col: int, rowspan: int = 1, colspan: int = 1, sticky: str = "nsew") -> tk.Frame:
        painel = tk.Frame(parent, bg=CORES["painel"], highlightbackground=CORES["borda"], highlightthickness=1)
        painel.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, sticky=sticky, padx=7, pady=7)
        return painel

    def _card(self, parent: tk.Misc, chave: str, titulo: str, row: int, col: int) -> None:
        painel = self._painel(parent, row, col)
        tk.Label(painel, text=titulo, bg=CORES["painel"], fg=CORES["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(12, 2))
        valor = tk.Label(painel, text="--", bg=CORES["painel"], fg=CORES["texto"], font=("Segoe UI Semibold", 18))
        valor.pack(anchor="w", padx=14, pady=(0, 12))
        self.cards[chave] = valor
        self.card_paineis[chave] = painel

    def _texto_painel(self, parent: tk.Misc, chave: str, row: int, col: int, titulo: str, height: int = 8, colspan: int = 1) -> None:
        painel = self._painel(parent, row, col, colspan=colspan)
        tk.Label(painel, text=titulo, bg=CORES["painel"], fg=CORES["texto"], font=("Segoe UI Semibold", 12)).pack(anchor="w", padx=16, pady=(14, 6))
        texto = self.criar_painel_texto_operacional(painel, height)
        self.cards[chave] = texto  # type: ignore[assignment]
        self.paineis_texto[chave] = painel

    def criar_painel_texto_operacional(self, parent: tk.Misc, height: int = 8) -> ScrolledText:
        texto = ScrolledText(
            parent,
            height=height,
            bg="#08111D",
            fg=CORES["texto"],
            insertbackground=CORES["texto"],
            relief="flat",
            font=("Consolas", 11),
            padx=12,
            pady=10,
            wrap="word",
        )
        texto.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.aplicar_tags_texto(texto)
        return texto

    def aplicar_tags_texto(self, texto: ScrolledText) -> None:
        texto.tag_configure("titulo", foreground=CORES["azul"], font=("Consolas", 12, "bold"), spacing1=8, spacing3=5)
        texto.tag_configure("rotulo", foreground=CORES["azul"], font=("Consolas", 11, "bold"))
        texto.tag_configure("critico", foreground=CORES["vermelho"], font=("Consolas", 11, "bold"))
        texto.tag_configure("atencao", foreground=CORES["amarelo"], font=("Consolas", 11, "bold"))
        texto.tag_configure("info", foreground=CORES["azul"])
        texto.tag_configure("sucesso", foreground=CORES["verde"])
        texto.tag_configure("piora", foreground=CORES["vermelho"], font=("Consolas", 11, "bold"))
        texto.tag_configure("melhora", foreground=CORES["verde"], font=("Consolas", 11, "bold"))
        texto.tag_configure("estavel", foreground=CORES["muted"])
        texto.tag_configure("ia", foreground=CORES["azul"], font=("Consolas", 11, "bold"))
        texto.tag_configure("muted", foreground=CORES["muted"])
        for tag in ("critico", "piora", "atencao", "sucesso", "melhora", "estavel"):
            texto.tag_raise(tag)

    def _aplicar_severidade_card(self, chave: str, status: Any) -> None:
        cor = cor_por_status(status)
        if chave in self.cards:
            self.cards[chave].configure(fg=cor)
        if chave in self.card_paineis:
            self.card_paineis[chave].configure(highlightbackground=cor, highlightthickness=2)

    def _aplicar_severidade_painel(self, chave: str, status: Any) -> None:
        if chave in self.paineis_texto:
            self.paineis_texto[chave].configure(highlightbackground=cor_por_status(status), highlightthickness=2)

    def _criar_tabela(self, parent: tk.Misc, chave: str, colunas: list[str], row: int, col: int, colspan: int = 1, height: int = 9) -> None:
        painel = self._painel(parent, row, col, colspan=colspan)
        tabela = ttk.Treeview(painel, columns=colunas, show="headings", height=height, style="Dark.Treeview")
        for coluna in colunas:
            tabela.heading(coluna, text=coluna)
            tabela.column(coluna, anchor="center", width=110, stretch=True)
        self._ajustar_colunas_tabela(chave, tabela)
        tabela.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabelas[chave] = tabela

    def _ajustar_colunas_tabela(self, chave: str, tabela: ttk.Treeview) -> None:
        larguras = {
            "eventos": {
                "ID": 50,
                "Tempo": 80,
                "Atualização": 90,
                "Severidade": 100,
                "Sistema": 150,
                "Mensagem": 220,
                "Diagnóstico": 220,
                "Ação": 260,
                "Reconhecido": 100,
            },
            "eventos_comunicacao": {
                "Tempo": 90,
                "Atualização": 90,
                "Severidade": 110,
                "Mensagem": 300,
                "Ação recomendada": 380,
            },
            "historico_bruto": {
                "Atualização": 90,
                "Tempo": 90,
                "Telemetria": 280,
                "Energia": 260,
                "Eventos": 360,
                "Origem": 100,
            },
            "cargas": {
                "Carga": 240,
                "Consumo": 110,
                "Prioridade": 120,
                "Decisão": 160,
            },
        }.get(chave, {})
        for coluna, largura in larguras.items():
            if coluna in tabela["columns"]:
                tabela.column(coluna, width=largura, stretch=True)

    def _criar_grafico(self, parent: tk.Misc, chave: str, titulo: str, row: int, col: int, cor: str, colspan: int = 1) -> None:
        grafico = GraficoLinha(self._painel(parent, row, col, colspan=colspan), titulo, cor)
        grafico.pack(fill="both", expand=True, padx=10, pady=10)
        self.graficos[chave] = grafico

    def _botoes_controle(self, parent: tk.Misc) -> None:
        acoes = tk.Frame(parent, bg=CORES["painel"])
        acoes.pack(fill="x", padx=12, pady=12)
        botoes = [
            ("Avançar atualização", self.avancar_atualizacao),
            ("Executar até o fim", self.executar_ate_o_fim),
            ("Pausar simulação", self.pausar_simulacao),
            ("Reiniciar missão", self.reiniciar_simulacao),
        ]
        for texto, comando in botoes:
            botao = tk.Button(
                acoes,
                text=texto,
                command=comando,
                bg=CORES["painel3"],
                fg=CORES["texto"],
                relief="flat",
                padx=12,
                pady=8,
                activebackground=CORES["azul"],
            )
            botao.pack(side="left", padx=4)
            self.botoes_controle.append(botao)
        tk.Label(acoes, textvariable=self.operacao_ia_var, bg=CORES["painel"], fg=CORES["azul"], font=("Segoe UI Semibold", 10)).pack(side="right", padx=10)

    def _montar_cockpit(self) -> None:
        grade = self._frame_grade(4)
        self._configurar_linhas(grade, {0: 0, 1: 0, 2: 3, 3: 2})
        for col in range(4):
            self._card(grade, f"cockpit_{col}", ["Status geral", "Risco atual", "Autonomia estimada", "Principal alerta"][col], 0, col)
        painel_controle = self._painel(grade, 1, 0, colspan=4)
        self._botoes_controle(painel_controle)
        self._texto_painel(grade, "prioridades", 2, 0, "Prioridade operacional", 11, colspan=2)
        self._texto_painel(grade, "mudancas", 2, 2, "O que mudou agora", 11, colspan=2)
        self._criar_grafico(grade, "risco", "Risco por atualização", 3, 0, CORES["vermelho"])
        self._criar_grafico(grade, "bateria", "Bateria por atualização", 3, 1, CORES["verde"])
        self._criar_grafico(grade, "comunicacao", "Comunicação por atualização", 3, 2, CORES["azul"])
        self._criar_grafico(grade, "saldo_energia", "Saldo energético", 3, 3, CORES["amarelo"])

    def _montar_telemetria(self) -> None:
        grade = self._frame_grade(5)
        self._configurar_linhas(grade, {0: 0, 1: 3, 2: 2})
        titulos = ["Temperatura interna", "Comunicação com a base", "Sistema de energia", "Suporte de oxigênio", "Estabilidade operacional"]
        for indice, titulo in enumerate(titulos):
            self._card(grade, f"telemetria_{indice}", titulo, 0, indice)
        self._criar_tabela(grade, "telemetria", ["Atualização", "Tempo", "Temp.", "Com.", "Bateria", "Oxigênio", "Estab.", "Risco", "Status"], 1, 0, colspan=5)
        self._criar_grafico(grade, "temperatura", "Temperatura", 2, 0, CORES["amarelo"])
        self._criar_grafico(grade, "oxigenio", "Oxigênio", 2, 1, CORES["azul"])
        self._criar_grafico(grade, "estabilidade", "Estabilidade", 2, 2, CORES["violeta"])
        self._criar_grafico(grade, "risco", "Risco", 2, 3, CORES["vermelho"], colspan=2)

    def _montar_energia(self) -> None:
        grade = self._frame_grade(3)
        self._configurar_linhas(grade, {0: 0, 1: 0, 2: 2, 3: 3})
        for indice, titulo in enumerate(["Bateria atual", "Geração solar", "Consumo total", "Saldo energético", "Autonomia", "Modo energético"]):
            self._card(grade, f"energia_{indice}", titulo, indice // 3, indice % 3)
        self._criar_grafico(grade, "geracao_solar", "Geração solar", 2, 0, CORES["verde"])
        self._criar_grafico(grade, "consumo_total", "Consumo total", 2, 1, CORES["amarelo"])
        self._criar_grafico(grade, "autonomia", "Autonomia", 2, 2, CORES["azul"])
        self._criar_tabela(grade, "cargas", ["Carga", "Consumo", "Prioridade", "Decisão"], 3, 0, colspan=2, height=8)
        self._texto_painel(grade, "decisao_energia", 3, 2, "Decisão energética", 9)

    def _montar_eventos(self) -> None:
        grade = self._frame_grade(1)
        self._configurar_linhas(grade, {0: 0, 1: 4, 2: 2})
        filtros = tk.Frame(self._painel(grade, 0, 0), bg=CORES["painel"])
        filtros.pack(fill="x", padx=10, pady=10)
        filtros_eventos = [
            ("Todos", "Todos"),
            ("CRITICO", "CRÍTICO"),
            ("ATENCAO", "ATENÇÃO"),
            ("INFO", "INFO"),
        ]
        for valor, rotulo in filtros_eventos:
            tk.Radiobutton(
                filtros,
                text=rotulo,
                value=valor,
                variable=self.filtro_eventos,
                command=self.atualizar_alertas,
                bg=CORES["painel"],
                fg=CORES["texto"],
                selectcolor=CORES["painel2"],
                activebackground=CORES["painel"],
            ).pack(side="left", padx=8)
        tk.Button(filtros, text="Reconhecer alerta", command=self.reconhecer_alerta, bg=CORES["painel3"], fg=CORES["texto"], relief="flat").pack(side="right", padx=4)
        tk.Button(filtros, text="Reconhecer todos", command=self.reconhecer_todos, bg=CORES["painel3"], fg=CORES["texto"], relief="flat").pack(side="right", padx=4)
        self._criar_tabela(grade, "eventos", ["ID", "Tempo", "Atualização", "Severidade", "Sistema", "Mensagem", "Diagnóstico", "Ação", "Reconhecido"], 1, 0, height=14)
        self.tabelas["eventos"].bind("<<TreeviewSelect>>", lambda _evento: self._atualizar_detalhe_evento())
        self._texto_painel(grade, "detalhe_evento", 2, 0, "Evento selecionado", 9)

    def _montar_relatorio(self) -> None:
        grade = self._frame_grade(1)
        self._configurar_linhas(grade, {0: 1})
        painel = self._painel(grade, 0, 0)
        tk.Button(
            painel,
            text="Exportar relatório TXT",
            command=self.exportar_relatorio,
            bg=CORES["azul"],
            fg="#06111F",
            relief="flat",
            padx=12,
            pady=8,
        ).pack(anchor="e", padx=12, pady=10)
        texto = self.criar_painel_texto_operacional(painel, 28)
        self.cards["relatorio"] = texto  # type: ignore[assignment]

    def _montar_comunicacao(self) -> None:
        grade = self._frame_grade(3)
        self._configurar_linhas(grade, {0: 0, 1: 0, 2: 2, 3: 3})
        titulos = ["Status do link", "Qualidade do sinal", "Latência", "Perda de pacotes", "Último contato", "Estação base"]
        for indice, titulo in enumerate(titulos):
            self._card(grade, f"com_{indice}", titulo, indice // 3, indice % 3)
        self._criar_grafico(grade, "comunicacao", "Comunicação", 2, 0, CORES["azul"])
        self._criar_grafico(grade, "latencia", "Latência", 2, 1, CORES["amarelo"])
        self._criar_grafico(grade, "perda_pacotes", "Perda de pacotes", 2, 2, CORES["vermelho"])
        self._criar_tabela(
            grade,
            "eventos_comunicacao",
            ["Tempo", "Atualização", "Severidade", "Mensagem", "Ação recomendada"],
            3,
            0,
            colspan=3,
            height=9,
        )

    def _montar_ia(self) -> None:
        grade = self._frame_grade(2)
        self._configurar_linhas(grade, {0: 2, 1: 3})
        self._texto_painel(grade, "ia_logs", 0, 0, "Logs da IA", 15)
        self._texto_painel(grade, "ia_prompt", 0, 1, "Prompt enviado à IA", 15)
        self._texto_painel(grade, "ia_resposta_bruta", 1, 0, "Resposta bruta da IA", 16)
        self._texto_painel(grade, "ia_analise", 1, 1, "Análise operacional da IA", 16)

    def _montar_historico(self) -> None:
        grade = self._frame_grade(1)
        self._configurar_linhas(grade, {0: 1})
        self._criar_tabela(
            grade,
            "historico_bruto",
            ["Atualização", "Tempo", "Telemetria", "Energia", "Eventos", "Origem"],
            0,
            0,
            height=22,
        )

    def _ultima(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        if not self.estado.ultima_atualizacao:
            return None, None, None
        return (
            self.estado.ultima_atualizacao["telemetria"],
            self.estado.ultima_atualizacao["risco"],
            self.estado.ultima_atualizacao["energia"],
        )

    def avancar_atualizacao(self) -> None:
        self.estado.missao_pausada = False
        if self._deve_usar_thread_ia():
            self._avancar_atualizacao_async()
            return
        self.estado.avancar_atualizacao()
        self._verificar_analise_ia_automatica()
        self.atualizar_interface_completa()

    def executar_ate_o_fim(self) -> None:
        if self._deve_usar_thread_ia():
            self._execucao_continua_ia = True
            self._avancar_atualizacao_async(ao_finalizar=self._continuar_execucao_ia)
            return
        self.estado.executar_ate_o_fim()
        self._cancelar_automatico()
        self.atualizar_interface_completa()

    def pausar_simulacao(self) -> None:
        self._execucao_continua_ia = False
        self.estado.pausar_simulacao()
        self._cancelar_automatico()
        self.atualizar_interface_completa()

    def reiniciar_simulacao(self) -> None:
        self._execucao_continua_ia = False
        self.estado.reiniciar_simulacao()
        self._cancelar_automatico()
        self.atualizar_interface_completa()
        if self.estado.configuracao.modo_execucao == "automatico":
            self._agendar_automatico()

    def simular_falha_critica(self) -> None:
        self.estado.missao_pausada = False
        if self._deve_usar_thread_ia():
            self._executar_acao_ia_async("Gerando falha crítica com IA...", self.estado.simular_falha_critica)
            return
        self.estado.simular_falha_critica()
        self.atualizar_interface_completa()

    def _deve_usar_thread_ia(self) -> bool:
        return self.estado.configuracao.fonte_dados == "ia_regras" and self.estado.configuracao.modo_ia == "por_atualizacao"

    def _deve_gerar_analise_ia_automatica(self) -> bool:
        atualizacao = self.estado.atualizacao_atual
        return (
            atualizacao > 0
            and atualizacao % 3 == 0
            and atualizacao not in self.estado.analises_ia_por_atualizacao
            and not self._analise_em_execucao
        )

    def _verificar_analise_ia_automatica(self) -> None:
        if self._deve_gerar_analise_ia_automatica():
            self._solicitar_analise_ia_async()

    def _agendar_ui(self, callback: Any) -> bool:
        try:
            if not self.winfo_exists():
                return False
            self.after(0, callback)
            return True
        except (RuntimeError, tk.TclError):
            return False

    def _definir_botoes_controle(self, habilitado: bool) -> None:
        estado = "normal" if habilitado else "disabled"
        for botao in self.botoes_controle:
            try:
                botao.configure(state=estado)
            except tk.TclError:
                pass

    def _executar_acao_ia_async(self, mensagem: str, acao: Any, ao_finalizar: Any | None = None) -> None:
        if self._ia_em_execucao:
            return
        self._ia_em_execucao = True
        self.operacao_ia_var.set(mensagem)
        self._definir_botoes_controle(False)

        def trabalho() -> None:
            try:
                acao()
            finally:
                if not self._agendar_ui(lambda: self._finalizar_acao_ia(ao_finalizar)):
                    self._ia_em_execucao = False

        threading.Thread(target=trabalho, daemon=True).start()

    def _finalizar_acao_ia(self, ao_finalizar: Any | None = None) -> None:
        origem = self.estado.historico_ia[-1].get("origem", "") if self.estado.historico_ia else ""
        diagnostico = self.estado.historico_ia[-1].get("diagnostico", {}) if self.estado.historico_ia else {}
        if origem == "ia + regras":
            self.operacao_ia_var.set("Validando resposta... IA + regras aplicada.")
        elif origem:
            self.operacao_ia_var.set("Fallback usado nesta atualização.")
        else:
            self.operacao_ia_var.set("")
        if origem:
            self.registrar_linha_terminal_ia(
                f"Telemetria retornou em {diagnostico.get('tempo_resposta_s', 0)} s | validação: {diagnostico.get('motivo_validacao', 'sem dados')} | origem: {origem}"
            )
        self._ia_em_execucao = False
        self._definir_botoes_controle(True)
        self._verificar_analise_ia_automatica()
        self.atualizar_interface_completa()
        if ao_finalizar:
            ao_finalizar()

    def _avancar_atualizacao_async(self, ao_finalizar: Any | None = None) -> None:
        self._executar_acao_ia_async(
            "Gerando telemetria com IA...",
            self.estado.avancar_atualizacao,
            ao_finalizar,
        )

    def _continuar_execucao_ia(self) -> None:
        """Encadeia um ciclo de IA por vez para atualizar a interface entre eles."""
        if not self._execucao_continua_ia or self.estado.missao_pausada or self.estado.missao_finalizada:
            self._execucao_continua_ia = False
            return
        try:
            self.after(10, lambda: self._avancar_atualizacao_async(ao_finalizar=self._continuar_execucao_ia))
        except (RuntimeError, tk.TclError):
            self._execucao_continua_ia = False

    def _aquecer_modelo_async(self) -> None:
        self._executar_acao_ia_async("Aquecendo modelo Ollama...", self.estado.aquecer_modelo_ia)

    def _agendar_automatico(self) -> None:
        self._cancelar_automatico()
        if self.estado.missao_finalizada:
            return
        atraso_ms = int(self.estado.configuracao.escala_execucao_real_s * 1000)
        self._after_id = self.after(atraso_ms, self._tick_automatico)

    def _tick_automatico(self) -> None:
        self._after_id = None
        if not self.estado.missao_pausada and not self.estado.missao_finalizada:
            if self._deve_usar_thread_ia():
                self._avancar_atualizacao_async(ao_finalizar=self._agendar_automatico)
            else:
                self.estado.executar_automaticamente()
                self._verificar_analise_ia_automatica()
                self.atualizar_interface_completa()
                self._agendar_automatico()

    def _cancelar_automatico(self) -> None:
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def preparar_dados_interface_completa(self) -> dict[str, Any]:
        """Monta uma fotografia única dos dados usados por todas as abas."""
        telemetria, risco, energia = self._ultima()
        principal_alerta = self.estado.alertas_ativos[0]["mensagem"] if self.estado.alertas_ativos else "Sem alerta ativo"
        return {
            "atualizacao_atual": self.estado.atualizacao_atual,
            "status_geral": self.estado.status_geral,
            "cockpit": {
                "principal_alerta": principal_alerta,
                "prioridades": self._texto_prioridades(),
                "mudancas": self._texto_mudancas(),
            },
            "telemetria": list(self.estado.historico_telemetria),
            "energia": list(self.estado.historico_energia),
            "comunicacao": self.estado.analise_comunicacao_atual(),
            "eventos": list(self.estado.historico_eventos),
            "ia": {
                "terminal": self._texto_terminal_ia(),
                "prompt": self._texto_prompt_ia(),
                "analise": self._texto_ia_analise(permitir_thread=False),
            },
            "historico": list(self.estado.historico_telemetria),
            "graficos": self.estado.dados_para_graficos(),
            "ultima": {"telemetria": telemetria, "risco": risco, "energia": energia},
        }

    def atualizar_interface_completa(self) -> None:
        """Atualiza cache, cards, tabelas, gráficos e terminais do dashboard."""
        self.dados_interface_cache = self.preparar_dados_interface_completa()
        self.resumo_topo.configure(
            text=(
                f"{self.estado.configuracao.nome_missao} | "
                f"Atualização {self.estado.atualizacao_atual}/{self.estado.total_atualizacoes} | "
                f"T+{self.estado.tempo_decorrido_min} min | Restante {self.estado.tempo_restante_min} min"
            )
        )
        self.status_var.set(self.estado.status_geral)
        self.atualizar_cards()
        self.atualizar_graficos()
        self.atualizar_alertas()

    def atualizar_tudo(self) -> None:
        self.atualizar_interface_completa()

    def atualizar_cards(self) -> None:
        telemetria, risco, energia = self._ultima()
        principal_alerta = self.estado.alertas_ativos[0]["mensagem"] if self.estado.alertas_ativos else "Sem alerta ativo"
        if "cockpit_0" in self.cards:
            status_risco = risco["status"] if risco else "NOMINAL"
            status_autonomia = "CRITICO" if energia and energia["autonomia_horas"] < 4 else "ATENCAO" if energia and energia["autonomia_horas"] < 8 else "NOMINAL"
            status_alerta = self.estado.alertas_ativos[0]["severidade"] if self.estado.alertas_ativos else "NOMINAL"
            valores = [
                formatar_status(self.estado.status_geral),
                f"{risco['pontuacao'] if risco else 0} pts",
                f"{energia['autonomia_horas']:.2f} h" if energia else "--",
                principal_alerta,
            ]
            for i, valor in enumerate(valores):
                label = self.cards[f"cockpit_{i}"]
                label.configure(text=valor)
            for chave, status in {
                "cockpit_0": self.estado.status_geral,
                "cockpit_1": status_risco,
                "cockpit_2": status_autonomia,
                "cockpit_3": status_alerta,
            }.items():
                self._aplicar_severidade_card(chave, status)
            self._aplicar_severidade_painel("prioridades", self.estado.status_geral)
            self._aplicar_severidade_painel("mudancas", status_alerta if self.estado.alertas_ativos else "INFO")
            self._set_texto("prioridades", self._texto_prioridades())
            self._set_texto("mudancas", self._texto_mudancas())
        if telemetria and "telemetria_0" in self.cards:
            dados = [
                f"{telemetria['temperatura_interna']:.1f} °C",
                f"{telemetria['comunicacao_base']:.1f}%",
                f"{telemetria['bateria']:.1f}%",
                f"{telemetria['oxigenio']:.1f}%",
                f"{telemetria['estabilidade_operacional']:.1f}%",
            ]
            for i, valor in enumerate(dados):
                self.cards[f"telemetria_{i}"].configure(text=valor)
            for chave, status in {
                "telemetria_0": status_temperatura(float(telemetria["temperatura_interna"])),
                "telemetria_1": status_por_valor(float(telemetria["comunicacao_base"]), 85, 60),
                "telemetria_2": status_por_valor(float(telemetria["bateria"]), 70, 40),
                "telemetria_3": status_por_valor(float(telemetria["oxigenio"]), 90, 82),
                "telemetria_4": status_por_valor(float(telemetria["estabilidade_operacional"]), 85, 70),
            }.items():
                self._aplicar_severidade_card(chave, status)
            self._popular_tabela_telemetria()
        if telemetria and energia and "energia_0" in self.cards:
            dados_energia = [
                f"{telemetria['bateria']:.1f}%",
                f"{telemetria['geracao_solar']:.1f} W",
                f"{energia['consumo_total']:.1f} W",
                f"{energia['saldo_energia']:+.1f} W",
                f"{energia['autonomia_horas']:.2f} h",
                formatar_status(energia["modo_energetico"]),
            ]
            for i, valor in enumerate(dados_energia):
                self.cards[f"energia_{i}"].configure(text=valor)
            for chave, status in {
                "energia_0": status_por_valor(float(telemetria["bateria"]), 70, 40),
                "energia_1": "NOMINAL" if telemetria["geracao_solar"] >= energia["consumo_total"] else "ATENCAO",
                "energia_2": "INFO",
                "energia_3": status_saldo(float(energia["saldo_energia"])),
                "energia_4": "CRITICO" if energia["autonomia_horas"] < 4 else "ATENCAO" if energia["autonomia_horas"] < 8 else "NOMINAL",
                "energia_5": energia["modo_energetico"],
            }.items():
                self._aplicar_severidade_card(chave, status)
            self._aplicar_severidade_painel("decisao_energia", energia["status"])
            self._popular_tabela_cargas(energia)
            self._set_texto("decisao_energia", self._texto_decisao_energia(energia))
        if "com_0" in self.cards:
            com = self.estado.analise_comunicacao_atual()
            dados_com = [formatar_status(com["status"]), f"{com['qualidade']:.1f}%", f"{com['latencia']:.1f} ms", f"{com['perda']:.1f}%", com["ultimo_contato"], com["estacao"]]
            for i, valor in enumerate(dados_com):
                self.cards[f"com_{i}"].configure(text=valor)
            for chave, status in {
                "com_0": com["status"],
                "com_1": com["status"],
                "com_2": "CRITICO" if com["latencia"] > 800 else "ATENCAO" if com["latencia"] > 400 else "NOMINAL",
                "com_3": "CRITICO" if com["perda"] > 25 else "ATENCAO" if com["perda"] > 10 else "NOMINAL",
                "com_4": "INFO",
                "com_5": "INFO",
            }.items():
                self._aplicar_severidade_card(chave, status)
            self._popular_tabela_eventos_comunicacao()
        if "ia_logs" in self.cards:
            self._set_texto("ia_logs", self._texto_terminal_ia())
            self._set_texto("ia_prompt", self._texto_prompt_ia())
            self._set_texto("ia_resposta_bruta", self._texto_resposta_bruta_ia())
            self._set_texto("ia_analise", self._texto_ia_analise())
        if "relatorio" in self.cards:
            self._atualizar_relatorio_async()
        if "historico_bruto" in self.tabelas:
            self._popular_tabela_historico()

    def atualizar_graficos(self) -> dict[str, list[float]]:
        dados = self.estado.dados_para_graficos()
        for chave, grafico in self.graficos.items():
            serie = dados.get(chave, [])
            if serie:
                grafico.cor = self._cor_grafico(chave, float(serie[-1]))
            grafico.set_dados(dados.get(chave, []))
        return dados

    def _cor_grafico(self, chave: str, valor: float) -> str:
        return cor_por_status(self._status_grafico(chave, valor))

    def _status_grafico(self, chave: str, valor: float) -> str:
        if chave == "risco":
            if valor >= 6:
                return "CRITICO"
            if valor >= 3:
                return "ATENCAO"
            return "NOMINAL"
        if chave == "bateria":
            return status_por_valor(valor, 70, 40)
        if chave == "oxigenio":
            return status_por_valor(valor, 90, 82)
        if chave == "estabilidade":
            return status_por_valor(valor, 85, 70)
        if chave == "comunicacao":
            return status_por_valor(valor, 85, 60)
        if chave == "temperatura":
            return status_temperatura(valor)
        if chave == "saldo_energia":
            return status_saldo(valor)
        if chave == "autonomia":
            return "CRITICO" if valor < 4 else "ATENCAO" if valor < 8 else "NOMINAL"
        if chave == "latencia":
            return "CRITICO" if valor > 800 else "ATENCAO" if valor > 400 else "NOMINAL"
        if chave == "perda_pacotes":
            return "CRITICO" if valor > 25 else "ATENCAO" if valor > 10 else "NOMINAL"
        if chave in {"geracao_solar", "consumo_total"}:
            if not self.estado.historico_energia or not self.estado.historico_telemetria:
                return "NOMINAL"
            energia = self.estado.historico_energia[-1]
            telemetria = self.estado.historico_telemetria[-1]
            if energia["status"] == "CRITICO":
                return "CRITICO"
            return "NOMINAL" if telemetria["geracao_solar"] >= energia["consumo_total"] else "ATENCAO"
        return "NOMINAL"

    def atualizar_alertas(self) -> list[dict[str, object]]:
        if "eventos" in self.tabelas:
            self._popular_tabela_eventos()
        return self.estado.alertas_ativos

    def _set_texto(self, chave: str, conteudo: str) -> None:
        widget = self.cards.get(chave)
        if isinstance(widget, ScrolledText):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", conteudo)
            if chave == "ia_resposta_bruta":
                self.inserir_texto_neutro(widget)
            elif chave == "ia_prompt":
                self.inserir_linha_tecnica(widget)
            elif chave == "ia_logs":
                self.inserir_linha_log(widget)
            else:
                self.inserir_linha_com_severidade(widget)
            widget.configure(state="disabled")

    def inserir_texto_neutro(self, widget: ScrolledText) -> None:
        self._aplicar_cores_texto(widget, destacar_rotulos=False, destacar_status=False)

    def inserir_linha_tecnica(self, widget: ScrolledText) -> None:
        self._aplicar_cores_texto(widget, destacar_rotulos=True, destacar_status=False)

    def inserir_linha_log(self, widget: ScrolledText) -> None:
        self._aplicar_cores_texto(widget, destacar_rotulos=True, destacar_status=True, destacar_horario=True)

    def inserir_linha_com_severidade(self, widget: ScrolledText) -> None:
        self._aplicar_cores_texto(widget, destacar_rotulos=True, destacar_status=True)

    def _aplicar_cores_texto(
        self,
        widget: ScrolledText,
        destacar_rotulos: bool,
        destacar_status: bool,
        destacar_horario: bool = False,
    ) -> None:
        linhas = int(widget.index("end-1c").split(".")[0])
        titulos_conhecidos = {
            "RESUMO",
            "PRINCIPAL RISCO",
            "JUSTIFICATIVA",
            "PRIORIDADE OPERACIONAL",
            "PRÓXIMA AÇÃO",
            "OBSERVAÇÃO",
            "ALERTA",
            "DIAGNÓSTICO",
            "EVIDÊNCIA",
            "AÇÃO RECOMENDADA",
            "SISTEMA",
            "RECONHECIDO",
            "LOGS DA IA",
            "PROMPT ENVIADO À IA",
            "SYSTEM PROMPT",
            "INSTRUÇÃO PRINCIPAL",
            "CONTEXTO ENVIADO",
            "CONFIGURAÇÃO TÉCNICA",
            "PROMPT COMPLETO",
            "RESPOSTA BRUTA DA IA",
            "ANÁLISE OPERACIONAL DA IA",
            "DADOS DA MISSÃO",
            "RESULTADO OPERACIONAL",
            "ENERGIA",
            "COMUNICAÇÃO",
            "ALERTAS",
            "RECOMENDAÇÕES FINAIS",
            "ANÁLISE COMPLEMENTAR DA IA",
        }
        for numero in range(1, linhas + 1):
            inicio = f"{numero}.0"
            fim = f"{numero}.end"
            texto = widget.get(inicio, fim)
            upper = texto.strip().upper()
            if upper in titulos_conhecidos or (
                upper
                and len(upper) <= 52
                and upper == texto.strip()
                and any(c.isalpha() for c in upper)
                and not any(c in upper for c in "{}[]|:")
            ):
                widget.tag_add("titulo", inicio, fim)
            if destacar_rotulos:
                for correspondencia in re.finditer(r"(?<!\w)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 /_-]{1,30}:)", texto):
                    widget.tag_add(
                        "rotulo",
                        f"{numero}.{correspondencia.start(1)}",
                        f"{numero}.{correspondencia.end(1)}",
                    )
            if destacar_horario:
                horario = re.match(r"\[[0-9:]+\]", texto)
                if horario:
                    widget.tag_add("muted", f"{numero}.{horario.start()}", f"{numero}.{horario.end()}")

        if destacar_status:
            grupos = {
                "sucesso": [
                    "NORMAL",
                    "NOMINAL",
                    "ESTÁVEL",
                    "ESTAVEL",
                    "OPERANTE",
                    "ONLINE",
                    "APROVADA",
                    "VALIDADA",
                    "SUCESSO",
                    "MANTER ATIVA",
                    "MELHOROU",
                ],
                "atencao": [
                    "ATENÇÃO",
                    "ATENCAO",
                    "CONSERVAÇÃO",
                    "CONSERVACAO",
                    "FALLBACK",
                    "REDUZIR",
                    "ALERTA",
                ],
                "critico": [
                    "CRÍTICO",
                    "CRITICO",
                    "EMERGÊNCIA",
                    "EMERGENCIA",
                    "INDISPONÍVEL",
                    "INDISPONIVEL",
                    "FALHOU",
                    "FALHA",
                    "ESGOTADO",
                ],
                "piora": ["PIOROU"],
            }
            conteudo = widget.get("1.0", "end-1c")
            for tag, termos in grupos.items():
                for termo in termos:
                    padrao = rf"(?<![\wÀ-ÿ]){re.escape(termo)}(?![\wÀ-ÿ])"
                    for correspondencia in re.finditer(padrao, conteudo, flags=re.IGNORECASE):
                        inicio_tag = f"1.0+{correspondencia.start()}c"
                        fim_tag = f"1.0+{correspondencia.end()}c"
                        widget.tag_add(tag, inicio_tag, fim_tag)

    def _estado_p4_ia(self) -> tuple[str, str]:
        if self.estado.configuracao.fonte_dados != "ia_regras":
            return "INDISPONÍVEL", "Operar apenas com análise determinística."
        ultima_analise = self.estado.historico_analise_ia[-1] if self.estado.historico_analise_ia else {}
        if not ultima_analise:
            return "INDISPONÍVEL", "Aguardar a análise automática no próximo ciclo programado."
        if ultima_analise.get("origem") == "IA" and ultima_analise.get("fallback_usado") != "sim":
            return "OPERANTE", "Usar análise da IA como apoio à decisão operacional."
        if ultima_analise.get("fallback_usado") == "sim" or "fallback" in str(ultima_analise.get("origem", "")).lower():
            return "FALLBACK", "Manter decisões pelo motor determinístico e verificar logs da IA."
        return "INDISPONÍVEL", "Operar apenas com análise determinística."

    def _texto_prioridades(self) -> str:
        _telemetria, risco, energia = self._ultima()
        recomendacoes = self.estado.recomendacoes_prioritarias()
        status = risco["status"] if risco else "NOMINAL"
        energia_status = energia["status"] if energia else "NORMAL"
        comunicacao = self.estado.analise_comunicacao_atual()
        ia_status, ia_acao = self._estado_p4_ia()
        linhas = []
        blocos = [
            ("P1 — Sistema de energia", energia_status, recomendacoes[0] if recomendacoes else "Manter o monitoramento."),
            ("P2 — Suporte de oxigênio", status, recomendacoes[1] if len(recomendacoes) > 1 else "Acompanhar o suporte de vida."),
            ("P3 — Comunicação com a base", comunicacao["status"], recomendacoes[2] if len(recomendacoes) > 2 else "Manter o monitoramento do link."),
            ("P4 — AI Mission Advisor", ia_status, ia_acao),
        ]
        for titulo, status_bloco, acao in blocos:
            linhas.extend([titulo, f"Status: {formatar_status(status_bloco)}", f"Ação: {acao}", ""])
        return "\n".join(linhas).strip()

    def _texto_mudancas(self) -> str:
        comparacao = self.estado.comparar_ultima_atualizacao()
        if not comparacao:
            return "Primeira atualização: ainda não há comparação anterior."
        linhas = []
        for item in comparacao:
            delta = float(item["delta"])
            tendencia = str(item["tendencia"])
            if abs(delta) < 0.05:
                marcador = "ESTÁVEL"
                seta = "→"
            elif tendencia == "melhorou":
                marcador = "MELHOROU"
                seta = "↑"
            else:
                marcador = "PIOROU"
                seta = "↓"
            relevancia = "alteração relevante" if abs(delta) >= 5 else "variação leve"
            linhas.append(f"{marcador:<8} {item['nome']}: {delta:+.2f} {item['unidade']} {seta} {relevancia}")
        return "\n".join(linhas)

    def _texto_decisao_energia(self, energia: dict[str, Any]) -> str:
        telemetria, _risco, _energia = self._ultima()
        geracao = float(telemetria["geracao_solar"]) if telemetria else 0.0
        consumo = float(energia["consumo_total"])
        diferenca = geracao - consumo
        linhas = [
            "ALERTA",
            f"Status energético: {normalizar_status_visual(energia['status'])}",
            "",
            "DIAGNÓSTICO",
            f"Modo: {normalizar_status_visual(energia['modo_energetico'])}",
            f"Saldo {energia['saldo_energia']:+.1f} W e autonomia {energia['autonomia_horas']:.2f} h.",
            "",
            "EVIDÊNCIA",
            f"Geração solar: {geracao:.1f} W",
            f"Consumo total: {consumo:.1f} W",
            f"Diferença geração-consumo: {diferenca:+.1f} W",
            "",
            "AÇÃO RECOMENDADA",
        ]
        linhas.extend(f"- {item}" for item in energia["recomendacoes"])
        return "\n".join(linhas)

    def registrar_linha_terminal_ia(self, mensagem: str) -> None:
        horario = datetime.now().strftime("%H:%M:%S")
        self.terminal_ia_linhas.append(f"[{horario}] {mensagem}")
        self.terminal_ia_linhas = self.terminal_ia_linhas[-80:]

    def _texto_terminal_ia(self) -> str:
        if not self.terminal_ia_linhas:
            self.registrar_linha_terminal_ia(
                f"Logs da IA inicializados | IA ativa: {'sim' if self.estado.configuracao.fonte_dados == 'ia_regras' else 'não'}"
            )
            self.registrar_linha_terminal_ia(f"Modelo configurado: {MODELO_PADRAO_OLLAMA}")
        ultima = self.estado.historico_ia[-1] if self.estado.historico_ia else {}
        diagnostico = ultima.get("diagnostico", {})
        if diagnostico and not any(f"Atualização {self.estado.atualizacao_atual}" in linha for linha in self.terminal_ia_linhas[-6:]):
            self.registrar_linha_terminal_ia(
                " | ".join(
                    [
                        f"Atualização {self.estado.atualizacao_atual}",
                        "Chamada: geração de telemetria",
                        f"Tempo: {diagnostico.get('tempo_resposta_s', 0)}s",
                        f"Timeout: {diagnostico.get('timeout_usado', 'sem dados')}s",
                        f"Validação: {'aprovada' if diagnostico.get('validacao_ok') else 'fallback'}",
                        f"Origem final: {diagnostico.get('origem_final', ultima.get('origem', 'sem dados'))}",
                    ]
                )
            )
        return "Logs da IA\n\n" + "\n".join(self.terminal_ia_linhas)

    def _texto_prompt_ia(self) -> str:
        if self.estado.historico_analise_ia and self.estado.historico_analise_ia[-1].get("prompt"):
            analise = self.estado.historico_analise_ia[-1]
            return "\n\n".join(
                [
                    "Prompt enviado à IA",
                    "SYSTEM PROMPT",
                    analise.get("system_prompt", "Não registrado."),
                    "INSTRUÇÃO PRINCIPAL",
                    analise.get("instrucao_principal", "Não registrada."),
                    "CONTEXTO ENVIADO",
                    analise.get("contexto_ia", "Não registrado."),
                    "CONFIGURAÇÃO TÉCNICA",
                    analise.get("configuracao_tecnica", "Não registrada."),
                    "PROMPT COMPLETO",
                    analise["prompt"],
                ]
            )
        if self.estado.historico_ia:
            diagnostico = self.estado.historico_ia[-1].get("diagnostico", {})
            prompt = diagnostico.get("prompt", "")
            if prompt:
                return "\n\n".join(
                    [
                        "Prompt enviado à IA",
                        "SYSTEM PROMPT",
                        "Gerador de telemetria simulada do Mission Control AI.",
                        "INSTRUÇÃO PRINCIPAL",
                        prompt,
                        "CONFIGURAÇÃO TÉCNICA",
                        "\n".join(
                            [
                                f"Modelo: {diagnostico.get('modelo_usado', MODELO_PADRAO_OLLAMA)}",
                                f"Timeout: {diagnostico.get('timeout_usado', 'sem dados')} s",
                                "Tipo de chamada: geração de telemetria",
                                f"Atualização: {self.estado.atualizacao_atual}",
                            ]
                        ),
                    ]
                )
        return "Prompt enviado à IA\n\nNenhum prompt foi enviado nesta simulação."

    def _texto_resposta_bruta_ia(self) -> str:
        if self.estado.historico_analise_ia:
            resposta_bruta = self.estado.historico_analise_ia[-1].get("resposta_bruta", "")
            if resposta_bruta:
                return "Resposta bruta da IA\n\n" + resposta_bruta
            return "Resposta bruta da IA\n\nNenhuma resposta bruta disponível para esta chamada."
        if self.estado.historico_ia:
            resposta_bruta = str(self.estado.historico_ia[-1].get("json_bruto", ""))
            if resposta_bruta:
                return "Resposta bruta da IA\n\n" + resposta_bruta
        return "Resposta bruta da IA\n\nNenhuma resposta bruta disponível para esta chamada."

    def _texto_ia_status(self) -> str:
        status = verificar_status_ollama()
        modelo_encontrado = MODELO_PADRAO_OLLAMA in status["modelos"]
        ultima_telemetria = self.estado.historico_ia[-1] if self.estado.historico_ia else {}
        diagnostico = ultima_telemetria.get("diagnostico", {})
        ultima_analise = self.estado.historico_analise_ia[-1] if self.estado.historico_analise_ia else {}
        erro = ultima_analise.get("erro_tecnico") or ultima_telemetria.get("erro_tecnico") or status.get("erro") or "Nenhum"
        fallback = "sim" if ultima_telemetria.get("origem") != "ia + regras" or ultima_analise.get("fallback_usado") == "sim" else "não"
        return "\n".join(
            [
                f"IA ativa: {'sim' if self.estado.configuracao.fonte_dados == 'ia_regras' else 'não'}",
                f"Ollama: {'online' if status['online'] else 'offline'}",
                f"Modelo configurado: {MODELO_PADRAO_OLLAMA}",
                f"Modelo encontrado: {'sim' if modelo_encontrado else 'não'}",
                f"Origem da última telemetria: {ultima_telemetria.get('origem', 'sem dados')}",
                f"Origem da última análise: {ultima_analise.get('origem', 'sem dados')}",
                f"Fallback usado: {fallback}",
                f"Origem final: {diagnostico.get('origem_final', ultima_telemetria.get('origem', 'sem dados'))}",
                f"Tempo última chamada: {diagnostico.get('tempo_resposta_s', 0)}s",
                f"Timeout usado: {diagnostico.get('timeout_usado', 'sem dados')}s",
                f"Validação telemetria: {'OK' if diagnostico.get('validacao_ok') else 'pendente/reprovada'}",
                f"Último erro técnico: {erro}",
            ]
        )

    def _texto_ia_json(self) -> str:
        telemetria, _risco, _energia = self._ultima()
        if not telemetria:
            return "IA: aguardando telemetria.\nModo atual: preview/fallback."
        meta_ia = self.estado.historico_ia[-1] if self.estado.historico_ia else {}
        diagnostico = meta_ia.get("diagnostico", {})
        linhas = [
            f"IA ativa: {'sim' if self.estado.configuracao.fonte_dados == 'ia_regras' else 'não'}",
            "Modelo configurado: Ollama local opcional",
            f"Origem usada: {meta_ia.get('origem', 'regras internas')}",
            f"Validação: {meta_ia.get('validacao', 'sem validação registrada')}",
            f"Origem final: {diagnostico.get('origem_final', meta_ia.get('origem', 'sem dados'))}",
            f"Tempo de resposta: {diagnostico.get('tempo_resposta_s', 0)}s",
            f"Timeout usado: {diagnostico.get('timeout_usado', 'sem dados')}s",
            f"Consulta OK: {'sim' if diagnostico.get('consulta_ok') else 'não'}",
            f"Validação OK: {'sim' if diagnostico.get('validacao_ok') else 'não'}",
            f"Motivo do fallback: {diagnostico.get('motivo_validacao', meta_ia.get('erro_tecnico', 'Nenhum'))}",
            f"Chaves faltantes: {', '.join(diagnostico.get('chaves_faltantes', [])) or 'nenhuma'}",
            "",
            "CAMPOS PRINCIPAIS",
            f"Temperatura: {telemetria['temperatura_interna']} °C",
            f"Comunicação: {telemetria['comunicacao_base']}%",
            f"Bateria: {telemetria['bateria']}%",
            f"Oxigênio: {telemetria['oxigenio']}%",
            f"Estabilidade: {telemetria['estabilidade_operacional']}%",
            "",
            "JSON VALIDADO",
            "{",
        ]
        for chave, valor in telemetria.items():
            linhas.append(f'  "{chave}": {valor},')
        linhas.append("}")
        json_bruto = str(meta_ia.get("json_bruto", ""))
        if json_bruto:
            linhas.append("")
            linhas.append("JSON BRUTO RECEBIDO DO MODELO")
            linhas.append(json_bruto[:1200])
        return "\n".join(linhas)

    def _texto_ia_analise(self, permitir_thread: bool = True) -> str:
        resposta = self._obter_analise_ia(permitir_thread=permitir_thread)
        aviso_fallback = []
        if resposta.get("origem") not in {"IA", "em processamento"}:
            aviso_fallback = ["Análise por IA indisponível nesta chamada. Exibindo análise determinística.", ""]
        return "\n".join(
            aviso_fallback
            + [
                "RESUMO",
                resposta["resumo"],
                "",
                "PRINCIPAL RISCO",
                resposta["principal_risco"],
                "",
                "JUSTIFICATIVA",
                resposta["justificativa"],
                "",
                "PRIORIDADE OPERACIONAL",
                resposta["prioridade_operacional"],
                "",
                "PRÓXIMA AÇÃO",
                resposta["proxima_acao"],
                "",
                "OBSERVAÇÃO",
                resposta["observacao"],
                "",
                f"Origem: {resposta['origem']} | Modelo: {resposta.get('modelo', MODELO_PADRAO_OLLAMA)}",
            ]
        )

    def _obter_analise_ia(self, permitir_thread: bool = False) -> dict[str, str]:
        if self.estado.atualizacao_atual in self.estado.analises_ia_por_atualizacao:
            return self.estado.analises_ia_por_atualizacao[self.estado.atualizacao_atual]
        if self.estado.historico_analise_ia:
            return self.estado.historico_analise_ia[-1]
        if permitir_thread and self._deve_gerar_analise_ia_automatica():
            self._solicitar_analise_ia_async()
            return {
                "origem": "em processamento",
                "modelo": MODELO_PADRAO_OLLAMA,
                "resumo": "Gerando análise com IA...",
                "principal_risco": "Aguardando resposta.",
                "justificativa": "O dashboard continua responsivo enquanto o modelo processa o contexto.",
                "prioridade_operacional": "Aguardar validação da resposta.",
                "proxima_acao": "Manter monitoramento.",
                "observacao": "A análise será atualizada automaticamente ao retornar.",
            }
        return {
            "origem": "modo deterministico",
            "modelo": MODELO_PADRAO_OLLAMA,
            "resumo": (
                f"Missão em status {normalizar_status_visual(self.estado.status_geral)}, "
                f"com risco atual {self.estado.historico_risco[-1]['pontuacao'] if self.estado.historico_risco else 0}."
            ),
            "principal_risco": self.estado.alertas_ativos[0]["mensagem"] if self.estado.alertas_ativos else "Sem alerta ativo.",
            "justificativa": "Análise operacional aguardando o próximo ciclo múltiplo de 3.",
            "prioridade_operacional": self.estado.recomendacoes_prioritarias()[0],
            "proxima_acao": self.estado.recomendacoes_prioritarias()[0],
            "observacao": "A análise automática roda nos ciclos 3, 6, 9, 12, 15 e 18.",
        }

    def _solicitar_analise_ia_async(self) -> None:
        if self._analise_em_execucao:
            return
        self._analise_em_execucao = True
        atualizacao = self.estado.atualizacao_atual
        inicio = time.perf_counter()
        self.operacao_ia_var.set("Gerando análise da missão com IA...")
        self.registrar_linha_terminal_ia(f"Análise operacional da IA iniciada para atualização {atualizacao}.")

        def trabalho() -> None:
            try:
                self.estado.gerar_analise_ia()
            finally:
                duracao = time.perf_counter() - inicio
                if not self._agendar_ui(lambda: self._finalizar_analise_ia(atualizacao, duracao)):
                    self._analise_em_execucao = False

        threading.Thread(target=trabalho, daemon=True).start()

    def _finalizar_analise_ia(self, atualizacao: int | None = None, duracao_s: float | None = None) -> None:
        self._analise_em_execucao = False
        analise = (
            self.estado.analises_ia_por_atualizacao.get(atualizacao or -1)
            or (self.estado.historico_analise_ia[-1] if self.estado.historico_analise_ia else {})
        )
        duracao_texto = f"{duracao_s:.2f}s" if duracao_s is not None else "tempo não registrado"
        if analise.get("origem") == "IA":
            self.operacao_ia_var.set("Análise da IA validada.")
            self.registrar_linha_terminal_ia(f"Análise operacional concluída em {duracao_texto} | origem: IA")
        elif analise:
            self.operacao_ia_var.set("Fallback usado na análise.")
            self.registrar_linha_terminal_ia("Análise operacional falhou | fallback usado")
        self.atualizar_interface_completa()

    def _texto_contexto_ia(self) -> str:
        telemetria, risco, energia = self._ultima()
        linhas = [
            f"Atualização: {self.estado.atualizacao_atual}/{self.estado.total_atualizacoes}",
            f"Status geral: {normalizar_status_visual(self.estado.status_geral)}",
            f"Risco atual: {risco['pontuacao'] if risco else 0}",
            f"Telemetria atual: {telemetria or 'sem dados'}",
            f"Estado energético: {energia or 'sem dados'}",
            f"Alertas ativos: {[evento['mensagem'] for evento in self.estado.alertas_ativos]}",
            f"Recomendações determinísticas: {self.estado.recomendacoes_prioritarias()}",
        ]
        return "\n\n".join(linhas)

    def _atualizar_relatorio_async(self) -> None:
        if self._ultimo_relatorio_texto:
            self._set_texto("relatorio", self._ultimo_relatorio_texto)
        else:
            self._set_texto("relatorio", "Gerando relatório operacional...\n\nA interface permanece disponível durante a análise complementar da IA.")
        if self._relatorio_em_execucao:
            return
        self._relatorio_em_execucao = True

        def trabalho() -> None:
            texto = formatar_relatorio_texto(self.estado)
            if not self._agendar_ui(lambda: self._finalizar_relatorio(texto)):
                self._relatorio_em_execucao = False

        threading.Thread(target=trabalho, daemon=True).start()

    def _finalizar_relatorio(self, texto: str) -> None:
        self._ultimo_relatorio_texto = texto
        self._relatorio_em_execucao = False
        if "relatorio" in self.cards:
            self._set_texto("relatorio", texto)

    def _limpar_tabela(self, chave: str) -> ttk.Treeview:
        tabela = self.tabelas[chave]
        for item in tabela.get_children():
            tabela.delete(item)
        return tabela

    def _popular_tabela_telemetria(self) -> None:
        tabela = self._limpar_tabela("telemetria")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("NOMINAL", foreground=CORES["texto"])
        for indice, telemetria in enumerate(self.estado.historico_telemetria, start=1):
            risco = self.estado.historico_risco[indice - 1]
            tabela.insert(
                "",
                "end",
                tags=(risco["status"],),
                values=(
                    indice,
                    f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                    telemetria["temperatura_interna"],
                    telemetria["comunicacao_base"],
                    telemetria["bateria"],
                    telemetria["oxigenio"],
                    telemetria["estabilidade_operacional"],
                    risco["pontuacao"],
                    normalizar_status_visual(risco["status"]),
                ),
            )

    def _popular_tabela_cargas(self, energia: dict[str, Any]) -> None:
        tabela = self._limpar_tabela("cargas")
        tabela.tag_configure("manter", foreground=CORES["verde"])
        tabela.tag_configure("reduzir", foreground=CORES["amarelo"])
        tabela.tag_configure("cortar", foreground=CORES["vermelho"])
        for carga in energia["cargas"]:
            decisao = str(carga["decisao"])
            tag = "manter"
            if "reduzir" in decisao.lower():
                tag = "reduzir"
            elif "desativar" in decisao.lower() or "cortar" in decisao.lower():
                tag = "cortar"
            tabela.insert("", "end", tags=(tag,), values=(carga["nome"], f"{carga['consumo']:.1f} W", carga["prioridade"], decisao))

    def _popular_tabela_eventos(self) -> None:
        tabela = self._limpar_tabela("eventos")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("INFO", foreground=CORES["texto"])
        filtro = self.filtro_eventos.get()
        eventos = self.estado.motor_eventos.filtrar("todos" if filtro == "Todos" else filtro)
        for evento in eventos:
            tabela.insert(
                "",
                "end",
                tags=(evento["severidade"],),
                values=(
                    evento["id"],
                    f"T+{evento['tempo_missao']}",
                    evento["atualizacao"],
                    normalizar_status_visual(evento["severidade"]),
                    self._traduzir_sistema_evento(str(evento["sistema"])),
                    evento["mensagem"],
                    evento["diagnostico"],
                    evento["acao_recomendada"],
                    "Sim" if evento["reconhecido"] else "Não",
                ),
            )
        self._atualizar_detalhe_evento()

    def _traduzir_sistema_evento(self, sistema: str) -> str:
        nomes = {
            "temperatura_interna": "Temperatura interna",
            "comunicacao_base": "Comunicação com a base",
            "bateria": "Sistema de energia",
            "oxigenio": "Suporte de oxigênio",
            "estabilidade_operacional": "Estabilidade operacional",
            "Sistema de energia": "Sistema de energia",
            "Missao": "Missão",
            "Simulacao": "Simulação",
        }
        return nomes.get(sistema, sistema)

    def _atualizar_detalhe_evento(self) -> None:
        if "detalhe_evento" not in self.cards or "eventos" not in self.tabelas:
            return
        tabela = self.tabelas["eventos"]
        selecionado = tabela.selection()
        if selecionado:
            evento_id = int(tabela.item(selecionado[0], "values")[0])
            evento = next((item for item in self.estado.historico_eventos if item["id"] == evento_id), None)
        else:
            evento = self.estado.historico_eventos[-1] if self.estado.historico_eventos else None
        if not evento:
            self._set_texto("detalhe_evento", "Nenhum evento registrado.")
            self._aplicar_severidade_painel("detalhe_evento", "INFO")
            return
        self._aplicar_severidade_painel("detalhe_evento", evento["severidade"])
        conteudo = "\n".join(
            [
                "ALERTA",
                f"[{normalizar_status_visual(evento['severidade'])}] {evento['mensagem']}",
                "",
                "SISTEMA",
                self._traduzir_sistema_evento(str(evento["sistema"])),
                "",
                "DIAGNÓSTICO",
                evento["diagnostico"],
                "",
                "AÇÃO RECOMENDADA",
                evento["acao_recomendada"],
                "",
                "RECONHECIDO",
                "Sim" if evento["reconhecido"] else "Não",
            ]
        )
        self._set_texto("detalhe_evento", conteudo)

    def _popular_tabela_eventos_comunicacao(self) -> None:
        tabela = self._limpar_tabela("eventos_comunicacao")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("INFO", foreground=CORES["texto"])
        if not self.estado.historico_telemetria:
            tabela.insert("", "end", tags=("INFO",), values=("-", "-", "INFO", "Nenhum evento de comunicação foi registrado nesta missão.", "Aguardar a primeira leitura."))
            return

        linhas: list[tuple[str, int, str, str, str]] = []
        ultima_linha_info: tuple[str, int, str, str, str] | None = None
        for indice, telemetria in enumerate(self.estado.historico_telemetria, start=1):
            qualidade = float(telemetria["comunicacao_base"])
            latencia = float(telemetria["latencia_comunicacao_ms"])
            perda = float(telemetria["perda_pacotes_percentual"])
            if qualidade < 30 or perda > 25:
                severidade = "CRITICO"
                mensagem = "Comunicação crítica com a base."
                acao = "Priorizar o restabelecimento do link e reduzir o tráfego não essencial."
            elif qualidade < 60 or latencia > 800 or perda > 10:
                severidade = "ATENCAO"
                if latencia > 800:
                    mensagem = "Latência elevada no link de comunicação."
                elif perda > 10:
                    mensagem = "Perda de pacotes elevada."
                else:
                    mensagem = "Comunicação instável com a base."
                acao = "Monitorar a latência e a perda de pacotes; manter o canal de contingência pronto."
            else:
                severidade = "INFO"
                mensagem = "Comunicação estável."
                acao = "Manter o monitoramento do link."
            linha = (
                f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                indice,
                severidade,
                mensagem,
                acao,
            )
            if severidade == "INFO":
                ultima_linha_info = linha
            else:
                linhas.append(linha)
        if not linhas and ultima_linha_info:
            linhas = [ultima_linha_info]
        for tempo, indice, severidade, mensagem, acao in linhas[-10:]:
            tabela.insert(
                "",
                "end",
                tags=(severidade,),
                values=(
                    tempo,
                    indice,
                    normalizar_status_visual(severidade),
                    mensagem,
                    acao,
                ),
            )

    def _popular_tabela_historico(self) -> None:
        tabela = self._limpar_tabela("historico_bruto")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("INFO", foreground=CORES["texto"])
        for indice, telemetria in enumerate(self.estado.historico_telemetria, start=1):
            energia = self.estado.historico_energia[indice - 1]
            eventos = [e["mensagem"] for e in self.estado.historico_eventos if e["atualizacao"] == indice]
            severidades = [e["severidade"] for e in self.estado.historico_eventos if e["atualizacao"] == indice]
            tag = "CRITICO" if "CRITICO" in severidades else "ATENCAO" if "ATENCAO" in severidades else "INFO"
            origem = "IA + regras" if indice <= len(self.estado.historico_ia) and self.estado.historico_ia[indice - 1].get("origem") == "ia + regras" else "regras"
            tabela.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    indice,
                    f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                    f"T={telemetria['temperatura_interna']} °C | Com={telemetria['comunicacao_base']}%",
                    f"Bat={telemetria['bateria']}% | Saldo={energia['saldo_energia']:+.1f} W",
                    "; ".join(eventos[:2]) or "Sem evento",
                    origem,
                ),
            )

    def reconhecer_alerta(self) -> None:
        tabela = self.tabelas.get("eventos")
        if not tabela:
            return
        selecionado = tabela.selection()
        if not selecionado:
            return
        evento_id = int(tabela.item(selecionado[0], "values")[0])
        self.estado.motor_eventos.reconhecer_evento(evento_id)
        self.atualizar_alertas()

    def reconhecer_todos(self) -> None:
        self.estado.motor_eventos.reconhecer_todos()
        self.atualizar_alertas()

    def exportar_relatorio(self) -> None:
        caminho = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if not caminho:
            return
        Path(caminho).write_text(formatar_relatorio_texto(self.estado), encoding="utf-8")
        messagebox.showinfo("Relatório exportado", f"Arquivo salvo em:\n{caminho}")


def criar_estado_padrao() -> EstadoMissao:
    estado = EstadoMissao(criar_configuracao_por_preset("Orbita Terrestre"))
    estado.iniciar_simulacao()
    return estado


def main() -> None:
    DashboardMissaoApp(criar_estado_padrao(), iniciar_loop=True)


if __name__ == "__main__":
    main()
