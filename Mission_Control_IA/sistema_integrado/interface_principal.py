from __future__ import annotations

import sys
import threading
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
}

STATUS_ROTULOS = {
    "ATENCAO": "ATENÇÃO",
    "CRITICO": "CRÍTICO",
    "ESTAVEL": "ESTÁVEL",
    "CONTINGENCIA": "CONTINGÊNCIA",
    "SEM DADOS": "SEM DADOS",
}


def formatar_status(status: str) -> str:
    return STATUS_ROTULOS.get(status, status)


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
        self.create_text(largura - 14, 12, text=f"{self.series[-1]:.1f}", fill=self.cor, anchor="ne", font=("Segoe UI Semibold", 10))


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

    def _texto_painel(self, parent: tk.Misc, chave: str, row: int, col: int, titulo: str, height: int = 8, colspan: int = 1) -> None:
        painel = self._painel(parent, row, col, colspan=colspan)
        tk.Label(painel, text=titulo, bg=CORES["painel"], fg=CORES["texto"], font=("Segoe UI Semibold", 12)).pack(anchor="w", padx=16, pady=(14, 6))
        texto = self.criar_painel_texto_operacional(painel, height)
        self.cards[chave] = texto  # type: ignore[assignment]

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
        texto.tag_configure("critico", foreground=CORES["vermelho"], font=("Consolas", 11, "bold"))
        texto.tag_configure("atencao", foreground=CORES["amarelo"], font=("Consolas", 11, "bold"))
        texto.tag_configure("info", foreground=CORES["azul"])
        texto.tag_configure("sucesso", foreground=CORES["verde"])
        texto.tag_configure("ia", foreground=CORES["azul"], font=("Consolas", 11, "bold"))
        texto.tag_configure("muted", foreground=CORES["muted"])

    def _criar_tabela(self, parent: tk.Misc, chave: str, colunas: list[str], row: int, col: int, colspan: int = 1, height: int = 9) -> None:
        painel = self._painel(parent, row, col, colspan=colspan)
        tabela = ttk.Treeview(painel, columns=colunas, show="headings", height=height, style="Dark.Treeview")
        for coluna in colunas:
            tabela.heading(coluna, text=coluna)
            tabela.column(coluna, anchor="center", width=110, stretch=True)
        tabela.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabelas[chave] = tabela

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
        for col in range(4):
            self._card(grade, f"cockpit_{col}", ["Status geral", "Risco atual", "Autonomia estimada", "Principal alerta"][col], 0, col)
        painel_controle = self._painel(grade, 1, 0, colspan=4)
        self._botoes_controle(painel_controle)
        self._texto_painel(grade, "prioridades", 2, 0, "Prioridade operacional", 9, colspan=2)
        self._texto_painel(grade, "mudancas", 2, 2, "O que mudou agora", 9, colspan=2)
        self._criar_grafico(grade, "risco", "Risco por atualização", 3, 0, CORES["vermelho"])
        self._criar_grafico(grade, "bateria", "Bateria por atualização", 3, 1, CORES["verde"])
        self._criar_grafico(grade, "comunicacao", "Comunicação por atualização", 3, 2, CORES["azul"])
        self._criar_grafico(grade, "saldo_energia", "Saldo energético", 3, 3, CORES["amarelo"])

    def _montar_telemetria(self) -> None:
        grade = self._frame_grade(5)
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
        for indice, titulo in enumerate(["Bateria atual", "Geração solar", "Consumo total", "Saldo energético", "Autonomia", "Modo energético"]):
            self._card(grade, f"energia_{indice}", titulo, indice // 3, indice % 3)
        self._criar_grafico(grade, "geracao_solar", "Geração solar", 2, 0, CORES["verde"])
        self._criar_grafico(grade, "consumo_total", "Consumo total", 2, 1, CORES["amarelo"])
        self._criar_grafico(grade, "autonomia", "Autonomia", 2, 2, CORES["azul"])
        self._criar_tabela(grade, "cargas", ["Carga", "Consumo", "Prioridade", "Decisão"], 3, 0, colspan=2, height=6)
        self._texto_painel(grade, "decisao_energia", 3, 2, "Decisão energética", 6)

    def _montar_comunicacao(self) -> None:
        grade = self._frame_grade(3)
        for indice, titulo in enumerate(["Status do link", "Qualidade do sinal", "Latência", "Perda de pacotes", "Último contato", "Estação base"]):
            self._card(grade, f"com_{indice}", titulo, indice // 3, indice % 3)
        self._criar_grafico(grade, "comunicacao", "Comunicacao", 2, 0, CORES["azul"])
        self._criar_grafico(grade, "latencia", "Latencia", 2, 1, CORES["amarelo"])
        self._criar_grafico(grade, "perda_pacotes", "Perda de pacotes", 2, 2, CORES["vermelho"])
        self._criar_tabela(grade, "eventos_comunicacao", ["Tempo", "Severidade", "Mensagem", "Ação"], 3, 0, colspan=3, height=7)

    def _montar_eventos(self) -> None:
        grade = self._frame_grade(1)
        filtros = tk.Frame(self._painel(grade, 0, 0), bg=CORES["painel"])
        filtros.pack(fill="x", padx=10, pady=10)
        for filtro in ["Todos", "CRITICO", "ATENCAO", "INFO"]:
            tk.Radiobutton(
                filtros,
                text=filtro,
                value=filtro,
                variable=self.filtro_eventos,
                command=self.atualizar_alertas,
                bg=CORES["painel"],
                fg=CORES["texto"],
                selectcolor=CORES["painel2"],
                activebackground=CORES["painel"],
            ).pack(side="left", padx=8)
        tk.Button(filtros, text="Reconhecer alerta", command=self.reconhecer_alerta, bg=CORES["painel3"], fg=CORES["texto"], relief="flat").pack(side="right", padx=4)
        tk.Button(filtros, text="Reconhecer todos", command=self.reconhecer_todos, bg=CORES["painel3"], fg=CORES["texto"], relief="flat").pack(side="right", padx=4)
        self._criar_tabela(grade, "eventos", ["ID", "Tempo", "Atualização", "Severidade", "Sistema", "Mensagem", "Diagnóstico", "Ação", "Reconhecido"], 1, 0, height=12)
        self.tabelas["eventos"].bind("<<TreeviewSelect>>", lambda _evento: self._atualizar_detalhe_evento())
        self._texto_painel(grade, "detalhe_evento", 2, 0, "Evento selecionado", 8)

    def _montar_ia(self) -> None:
        grade = self._frame_grade(2)
        self._texto_painel(grade, "ia_status", 0, 0, "Status da IA", 8)
        self._texto_painel(grade, "ia_json", 0, 1, "Telemetria gerada por IA", 8)
        self._texto_painel(grade, "ia_analise", 1, 0, "Análise da missão por IA", 12)
        self._texto_painel(grade, "ia_contexto", 1, 1, "Contexto enviado à IA", 12)

    def _montar_relatorio(self) -> None:
        grade = self._frame_grade(1)
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
        texto = self.criar_painel_texto_operacional(painel, 24)
        self.cards["relatorio"] = texto  # type: ignore[assignment]

    def _montar_historico(self) -> None:
        grade = self._frame_grade(1)
        painel = self._painel(grade, 0, 0)
        self._botoes_controle(painel)
        tk.Button(
            painel,
            text="Simular falha crítica",
            command=self.simular_falha_critica,
            bg=CORES["vermelho"],
            fg=CORES["texto"],
            relief="flat",
            padx=12,
            pady=8,
        ).pack(anchor="w", padx=16, pady=(0, 12))
        self._criar_tabela(grade, "historico_bruto", ["Atualização", "Tempo", "Telemetria", "Energia", "Eventos"], 1, 0, height=16)

    def _montar_comunicacao(self) -> None:
        grade = self._frame_grade(3)
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
            height=7,
        )

    def _montar_ia(self) -> None:
        grade = self._frame_grade(2)
        self._texto_painel(grade, "ia_terminal", 0, 0, "Terminal da IA", 12)
        self._texto_painel(grade, "ia_prompt", 0, 1, "Prompt enviado à IA", 12)
        self._texto_painel(grade, "ia_analise", 1, 0, "Resposta / análise da IA", 14, colspan=2)

    def _montar_historico(self) -> None:
        grade = self._frame_grade(1)
        self._criar_tabela(
            grade,
            "historico_bruto",
            ["Atualização", "Tempo", "Telemetria", "Energia", "Eventos"],
            0,
            0,
            height=18,
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
                self.after(0, lambda: self._finalizar_acao_ia(ao_finalizar))

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
        self.after(10, lambda: self._avancar_atualizacao_async(ao_finalizar=self._continuar_execucao_ia))

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
            valores = [
                formatar_status(self.estado.status_geral),
                f"{risco['pontuacao'] if risco else 0} pts",
                f"{energia['autonomia_horas']:.2f} h" if energia else "--",
                principal_alerta,
            ]
            for i, valor in enumerate(valores):
                label = self.cards[f"cockpit_{i}"]
                label.configure(text=valor, fg=STATUS_CORES.get(str(valor), CORES["texto"]))
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
            self._popular_tabela_cargas(energia)
            self._set_texto("decisao_energia", self._texto_decisao_energia(energia))
        if "com_0" in self.cards:
            com = self.estado.analise_comunicacao_atual()
            dados_com = [formatar_status(com["status"]), f"{com['qualidade']:.1f}%", f"{com['latencia']:.1f} ms", f"{com['perda']:.1f}%", com["ultimo_contato"], com["estacao"]]
            for i, valor in enumerate(dados_com):
                self.cards[f"com_{i}"].configure(text=valor, fg=STATUS_CORES.get(str(valor), CORES["texto"]))
            self._popular_tabela_eventos_comunicacao()
        if "ia_terminal" in self.cards:
            self._set_texto("ia_terminal", self._texto_terminal_ia())
            self._set_texto("ia_prompt", self._texto_prompt_ia())
            self._set_texto("ia_analise", self._texto_ia_analise())
        if "relatorio" in self.cards:
            self._atualizar_relatorio_async()
        if "historico_bruto" in self.tabelas:
            self._popular_tabela_historico()

    def atualizar_graficos(self) -> dict[str, list[float]]:
        dados = self.estado.dados_para_graficos()
        for chave, grafico in self.graficos.items():
            grafico.set_dados(dados.get(chave, []))
        return dados

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
            self.inserir_linha_com_severidade(widget)
            widget.configure(state="disabled")

    def inserir_linha_com_severidade(self, widget: ScrolledText) -> None:
        linhas = int(widget.index("end-1c").split(".")[0])
        for numero in range(1, linhas + 1):
            inicio = f"{numero}.0"
            fim = f"{numero}.end"
            texto = widget.get(inicio, fim)
            upper = texto.upper()
            if upper.strip().endswith(":") or upper in {"RESUMO", "PRINCIPAL RISCO", "JUSTIFICATIVA", "PRIORIDADE OPERACIONAL", "PRÓXIMA AÇÃO", "OBSERVAÇÃO"}:
                widget.tag_add("titulo", inicio, fim)
            elif "CRITICO" in upper or "CRÍTICO" in upper or "[CRITICO]" in upper:
                widget.tag_add("critico", inicio, fim)
            elif "ATENCAO" in upper or "ATENÇÃO" in upper or "FALLBACK" in upper:
                widget.tag_add("atencao", inicio, fim)
            elif "IA" in upper or "OLLAMA" in upper:
                widget.tag_add("ia", inicio, fim)
            elif "NOMINAL" in upper or "VALIDADA" in upper or "ONLINE" in upper:
                widget.tag_add("sucesso", inicio, fim)

    def _texto_prioridades(self) -> str:
        _telemetria, risco, energia = self._ultima()
        recomendacoes = self.estado.recomendacoes_prioritarias()
        status = risco["status"] if risco else "NOMINAL"
        energia_status = energia["status"] if energia else "NORMAL"
        comunicacao = self.estado.analise_comunicacao_atual()
        linhas = []
        blocos = [
            ("P1 — Sistema de energia", energia_status, recomendacoes[0] if recomendacoes else "Manter o monitoramento."),
            ("P2 — Suporte de oxigênio", status, recomendacoes[1] if len(recomendacoes) > 1 else "Acompanhar o suporte de vida."),
            ("P3 — Comunicação com a base", comunicacao["status"], recomendacoes[2] if len(recomendacoes) > 2 else "Manter o monitoramento do link."),
            (
                "P4 — AI Mission Advisor",
                "IA",
                self.estado.historico_analise_ia[-1].get("proxima_acao", "Aguardar análise da IA.")
                if self.estado.historico_analise_ia
                else "Aguardar análise da IA.",
            ),
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
            seta = "→"
            if abs(item["delta"]) >= 0.05:
                seta = "↑" if item["tendencia"] == "melhorou" else "↓"
            linhas.append(f"{item['nome']}: {item['delta']:+.2f} {item['unidade']} {seta} {item['tendencia']}")
        return "\n".join(linhas)

    def _texto_decisao_energia(self, energia: dict[str, Any]) -> str:
        linhas = [
            "ALERTA",
            f"Status energético: {energia['status']}",
            "",
            "DIAGNÓSTICO",
            f"Modo: {energia['modo_energetico']}",
            f"Saldo {energia['saldo_energia']:+.1f} W e autonomia {energia['autonomia_horas']:.2f} h.",
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
                f"Terminal da IA inicializado | IA ativa: {'sim' if self.estado.configuracao.fonte_dados == 'ia_regras' else 'não'}"
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
        return "Terminal da IA\n\n" + "\n".join(self.terminal_ia_linhas)

    def _texto_prompt_ia(self) -> str:
        if self.estado.historico_analise_ia and self.estado.historico_analise_ia[-1].get("prompt"):
            return "Prompt de análise da missão\n\n" + self.estado.historico_analise_ia[-1]["prompt"]
        if self.estado.historico_ia:
            prompt = self.estado.historico_ia[-1].get("diagnostico", {}).get("prompt", "")
            if prompt:
                return "Prompt de geração de telemetria\n\n" + prompt
        return "Prompt enviado à IA\n\nNenhum prompt foi enviado nesta simulação."

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
        if self.estado.historico_analise_ia and self.estado.historico_analise_ia[-1].get("atualizacao") == str(self.estado.atualizacao_atual):
            return self.estado.historico_analise_ia[-1]
        if permitir_thread:
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
            "resumo": f"Missão em status {self.estado.status_geral}, com risco atual {self.estado.historico_risco[-1]['pontuacao'] if self.estado.historico_risco else 0}.",
            "principal_risco": self.estado.alertas_ativos[0]["mensagem"] if self.estado.alertas_ativos else "Sem alerta ativo.",
            "justificativa": "Análise aguardando abertura ou retorno da chamada de IA.",
            "prioridade_operacional": self.estado.recomendacoes_prioritarias()[0],
            "proxima_acao": self.estado.recomendacoes_prioritarias()[0],
            "observacao": "A IA será acionada quando a seção de análise estiver aberta.",
        }

    def _solicitar_analise_ia_async(self) -> None:
        if self._analise_em_execucao:
            return
        self._analise_em_execucao = True
        self.operacao_ia_var.set("Gerando análise da missão com IA...")

        def trabalho() -> None:
            try:
                self.estado.gerar_analise_ia()
            finally:
                self.after(0, self._finalizar_analise_ia)

        threading.Thread(target=trabalho, daemon=True).start()

    def _finalizar_analise_ia(self) -> None:
        self._analise_em_execucao = False
        analise = self.estado.historico_analise_ia[-1] if self.estado.historico_analise_ia else {}
        if analise.get("origem") == "IA":
            self.operacao_ia_var.set("Análise da IA validada.")
        elif analise:
            self.operacao_ia_var.set("Fallback usado na análise.")
        self.atualizar_interface_completa()

    def _texto_contexto_ia(self) -> str:
        telemetria, risco, energia = self._ultima()
        linhas = [
            f"Atualização: {self.estado.atualizacao_atual}/{self.estado.total_atualizacoes}",
            f"Status geral: {self.estado.status_geral}",
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
            self.after(0, lambda: self._finalizar_relatorio(texto))

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
        for indice, telemetria in enumerate(self.estado.historico_telemetria, start=1):
            risco = self.estado.historico_risco[indice - 1]
            tabela.insert(
                "",
                "end",
                values=(
                    indice,
                    f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                    telemetria["temperatura_interna"],
                    telemetria["comunicacao_base"],
                    telemetria["bateria"],
                    telemetria["oxigenio"],
                    telemetria["estabilidade_operacional"],
                    risco["pontuacao"],
                    risco["status"],
                ),
            )

    def _popular_tabela_cargas(self, energia: dict[str, Any]) -> None:
        tabela = self._limpar_tabela("cargas")
        for carga in energia["cargas"]:
            tabela.insert("", "end", values=(carga["nome"], f"{carga['consumo']:.1f} W", carga["prioridade"], carga["decisao"]))

    def _popular_tabela_eventos(self) -> None:
        tabela = self._limpar_tabela("eventos")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("INFO", foreground=CORES["azul"])
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
                    evento["severidade"],
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
            return
        conteudo = "\n".join(
            [
                "ALERTA",
                f"[{evento['severidade']}] {evento['mensagem']}",
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
        for evento in self.estado.historico_eventos:
            sistema = str(evento["sistema"]).lower()
            mensagem = str(evento["mensagem"]).lower()
            if "comunic" in sistema or "comunic" in mensagem or "link" in mensagem:
                tabela.insert("", "end", values=(f"T+{evento['tempo_missao']}", evento["severidade"], evento["mensagem"], evento["acao_recomendada"]))

    def _popular_tabela_eventos_comunicacao(self) -> None:
        tabela = self._limpar_tabela("eventos_comunicacao")
        tabela.tag_configure("CRITICO", foreground=CORES["vermelho"])
        tabela.tag_configure("ATENCAO", foreground=CORES["amarelo"])
        tabela.tag_configure("INFO", foreground=CORES["azul"])
        if not self.estado.historico_telemetria:
            tabela.insert("", "end", tags=("INFO",), values=("-", "-", "INFO", "Nenhum evento de comunicação foi registrado nesta missão.", "Aguardar a primeira leitura."))
            return

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
            tabela.insert(
                "",
                "end",
                tags=(severidade,),
                values=(
                    f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                    indice,
                    severidade,
                    mensagem,
                    acao,
                ),
            )

    def _popular_tabela_historico(self) -> None:
        tabela = self._limpar_tabela("historico_bruto")
        for indice, telemetria in enumerate(self.estado.historico_telemetria, start=1):
            energia = self.estado.historico_energia[indice - 1]
            eventos = [e["mensagem"] for e in self.estado.historico_eventos if e["atualizacao"] == indice]
            tabela.insert(
                "",
                "end",
                values=(
                    indice,
                    f"T+{indice * self.estado.configuracao.intervalo_monitoramento_min}",
                    f"T={telemetria['temperatura_interna']} °C | Com={telemetria['comunicacao_base']}%",
                    f"Bat={telemetria['bateria']}% | Saldo={energia['saldo_energia']:+.1f} W",
                    "; ".join(eventos[:2]) or "Sem evento",
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
