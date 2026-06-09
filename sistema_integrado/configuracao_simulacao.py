from __future__ import annotations

from dataclasses import dataclass


MODOS_EXECUCAO = {"manual", "automatico"}
FONTES_DADOS = {"regras", "ia_regras"}
MODOS_IA = {"por_atualizacao", "pre_geracao_futura_desativada"}


@dataclass(frozen=True)
class PresetMissao:
    nome: str
    duracao_minutos: int
    intervalo_monitoramento_min: int
    perfil_risco: str
    energia_inicial: float
    comunicacao_inicial: float
    oxigenio_inicial: float
    estabilidade_inicial: float
    foco: str


@dataclass
class ConfiguracaoMissao:
    nome_missao: str
    duracao_minutos: int
    intervalo_monitoramento_min: int
    escala_execucao_real_s: float
    modo_execucao: str
    perfil_risco: str
    energia_inicial: float
    comunicacao_inicial: float
    oxigenio_inicial: float
    estabilidade_inicial: float
    fonte_dados: str = "regras"
    eventos_criticos: bool = True
    timeout_telemetria_ia: float = 60.0
    timeout_analise_ia: float = 60.0
    aquecer_modelo_ao_iniciar: bool = False
    modo_ia: str = "por_atualizacao"

    def __post_init__(self) -> None:
        if self.intervalo_monitoramento_min <= 0:
            raise ValueError("Intervalo de monitoramento deve ser positivo.")
        if self.duracao_minutos < self.intervalo_monitoramento_min:
            raise ValueError("A duração simulada deve ser maior ou igual ao intervalo.")
        if self.escala_execucao_real_s <= 0:
            raise ValueError("A escala real deve ser positiva.")
        if self.modo_execucao not in MODOS_EXECUCAO:
            raise ValueError("Modo de execução inválido.")
        if self.fonte_dados not in FONTES_DADOS:
            raise ValueError("Fonte de dados inválida.")
        if self.timeout_telemetria_ia <= 0 or self.timeout_analise_ia <= 0:
            raise ValueError("Os timeouts da IA devem ser positivos.")
        if self.modo_ia not in MODOS_IA:
            raise ValueError("Modo de IA inválido.")
        for valor in [self.energia_inicial, self.comunicacao_inicial, self.oxigenio_inicial, self.estabilidade_inicial]:
            if not 0 <= valor <= 100:
                raise ValueError("Os valores percentuais iniciais devem estar entre 0 e 100.")

    @property
    def total_atualizacoes(self) -> int:
        return calcular_total_atualizacoes(self.duracao_minutos, self.intervalo_monitoramento_min)


PRESETS_MISSAO = {
    "Ida a Lua": PresetMissao("Ida a Lua", 180, 10, "degradacao_progressiva", 88, 86, 96, 90, "energia, comunicacao e estabilidade"),
    "Orbita Terrestre": PresetMissao("Orbita Terrestre", 90, 5, "nominal", 92, 94, 98, 93, "monitoramento estavel"),
    "Operacao de Capsula": PresetMissao("Operacao de Capsula", 60, 5, "suporte_vida", 85, 88, 96, 86, "temperatura e oxigenio"),
    "Sobrevoo Lunar": PresetMissao("Sobrevoo Lunar", 120, 10, "comunicacao_instavel", 82, 72, 94, 84, "comunicacao e estabilidade"),
    "Emergencia Simulada": PresetMissao("Emergencia Simulada", 45, 5, "critico", 68, 70, 90, 78, "falhas planejadas"),
}


def calcular_total_atualizacoes(duracao_minutos: int, intervalo_monitoramento_min: int) -> int:
    if intervalo_monitoramento_min <= 0:
        raise ValueError("Intervalo deve ser positivo.")
    if duracao_minutos < intervalo_monitoramento_min:
        raise ValueError("A duração deve ser maior ou igual ao intervalo.")
    return duracao_minutos // intervalo_monitoramento_min


def criar_configuracao_por_preset(nome_preset: str, **substituicoes: object) -> ConfiguracaoMissao:
    if nome_preset not in PRESETS_MISSAO:
        raise ValueError(f"Missão predefinida desconhecida: {nome_preset}")
    preset = PRESETS_MISSAO[nome_preset]
    dados = {
        "nome_missao": preset.nome,
        "duracao_minutos": preset.duracao_minutos,
        "intervalo_monitoramento_min": preset.intervalo_monitoramento_min,
        "escala_execucao_real_s": 2.0,
        "modo_execucao": "manual",
        "perfil_risco": preset.perfil_risco,
        "energia_inicial": preset.energia_inicial,
        "comunicacao_inicial": preset.comunicacao_inicial,
        "oxigenio_inicial": preset.oxigenio_inicial,
        "estabilidade_inicial": preset.estabilidade_inicial,
        "fonte_dados": "regras",
        "eventos_criticos": True,
        "timeout_telemetria_ia": 60.0,
        "timeout_analise_ia": 60.0,
        "aquecer_modelo_ao_iniciar": False,
        "modo_ia": "por_atualizacao",
    }
    dados.update(substituicoes)
    return ConfiguracaoMissao(**dados)
