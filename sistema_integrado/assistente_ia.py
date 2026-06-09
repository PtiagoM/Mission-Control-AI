from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from .gerador_telemetria import CHAVES_TELEMETRIA, limitar


"""Assistente local da IA.

Este arquivo concentra o contato com Ollama, a validação das respostas em JSON e
os fallbacks determinísticos. A IA ajuda a gerar telemetria e análise, mas o
estado operacional continua sendo validado pelas regras internas do sistema.
"""

LIMITES = {
    "temperatura_interna": (-20, 90),
    "comunicacao_base": (0, 100),
    "bateria": (0, 100),
    "oxigenio": (0, 100),
    "estabilidade_operacional": (0, 100),
    "geracao_solar": (0, float("inf")),
    "consumo_suporte_vida": (0, float("inf")),
    "consumo_comunicacao": (0, float("inf")),
    "consumo_estabilidade": (0, float("inf")),
    "consumo_pesquisa": (0, float("inf")),
    "latencia_comunicacao_ms": (0, float("inf")),
    "perda_pacotes_percentual": (0, 100),
}

MODELO_PADRAO_OLLAMA = os.getenv("MISSION_CONTROL_IA_MODELO", "llama3.2:1b")
URL_OLLAMA = os.getenv("MISSION_CONTROL_IA_OLLAMA_URL", "http://localhost:11434/api/generate")
URL_OLLAMA_TAGS = URL_OLLAMA.replace("/api/generate", "/api/tags")
TIMEOUT_STATUS_OLLAMA = float(os.getenv("MISSION_CONTROL_IA_TIMEOUT_STATUS", "1.5"))
TIMEOUT_TELEMETRIA_IA = float(os.getenv("MISSION_CONTROL_IA_TIMEOUT_TELEMETRIA", "60.0"))
TIMEOUT_ANALISE_IA = float(os.getenv("MISSION_CONTROL_IA_TIMEOUT_ANALISE", "60.0"))
TIMEOUT_RELATORIO_IA = float(os.getenv("MISSION_CONTROL_IA_TIMEOUT_RELATORIO", "60.0"))
CHAVES_ANALISE = [
    "resumo",
    "principal_risco",
    "justificativa",
    "prioridade_operacional",
    "proxima_acao",
    "nivel_confianca",
    "observacao",
]

SYSTEM_PROMPT_ANALISE = (
    "Voce e um assistente de operacao de missao espacial. "
    "Analise apenas os dados calculados pelo sistema; nao invente telemetria e nao altere risco, status, energia ou eventos."
)
INSTRUCAO_ANALISE = "Use frases curtas, claras e adequadas para um operador humano. Responda somente em JSON valido."


def _resumir_erro_tecnico(erro: Any) -> str:
    texto = str(erro)
    if "Connection refused" in texto or "WinError 10061" in texto:
        return "Ollama offline ou recusando conexao."
    if "timed out" in texto.lower():
        return "Tempo de resposta do Ollama esgotado."
    if "404" in texto:
        return "Endpoint ou modelo não encontrado no Ollama."
    return texto[:180]


def verificar_status_ollama(timeout_s: float = TIMEOUT_STATUS_OLLAMA) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(URL_OLLAMA_TAGS, timeout=timeout_s) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
        return {"online": False, "modelos": [], "erro": _resumir_erro_tecnico(erro)}
    modelos = [str(modelo.get("name", "")) for modelo in corpo.get("models", []) if modelo.get("name")]
    return {"online": True, "modelos": modelos, "erro": ""}


def listar_modelos_ollama(timeout_s: float = TIMEOUT_STATUS_OLLAMA) -> list[str]:
    return list(verificar_status_ollama(timeout_s)["modelos"])


def modelo_esta_disponivel(nome_modelo: str, timeout_s: float = TIMEOUT_STATUS_OLLAMA) -> bool:
    modelos = listar_modelos_ollama(timeout_s)
    return nome_modelo in modelos or any(modelo.split(":")[0] == nome_modelo for modelo in modelos)


def validar_telemetria_ia(texto: str) -> dict[str, Any]:
    def resposta_invalida(motivo: str, dados_recebidos: Any = None) -> dict[str, Any]:
        chaves_recebidas = sorted(dados_recebidos) if isinstance(dados_recebidos, dict) else []
        chaves_faltantes = [chave for chave in CHAVES_TELEMETRIA if chave not in chaves_recebidas]
        return {
            "valido": False,
            "motivo": motivo,
            "telemetria": None,
            "chaves_recebidas": chaves_recebidas,
            "chaves_faltantes": chaves_faltantes,
        }

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        inicio = texto.find("{")
        fim = texto.rfind("}")
        if inicio >= 0 and fim > inicio:
            try:
                dados = json.loads(texto[inicio : fim + 1])
            except json.JSONDecodeError:
                return resposta_invalida("A resposta da IA não está em JSON.")
        else:
            return resposta_invalida("A resposta da IA não está em JSON.")
    if isinstance(dados, list) and len(dados) == 1:
        dados = dados[0]
    if not isinstance(dados, dict):
        return resposta_invalida("JSON deve ser um objeto.")

    for chave_wrapper in ("telemetria", "dados", "leitura"):
        if isinstance(dados.get(chave_wrapper), dict):
            dados = dados[chave_wrapper]
            break

    chaves_recebidas = sorted(dados)
    chaves_faltantes = [chave for chave in CHAVES_TELEMETRIA if chave not in dados]
    if chaves_faltantes:
        return {
            "valido": False,
            "motivo": "JSON incompleto.",
            "telemetria": None,
            "chaves_recebidas": chaves_recebidas,
            "chaves_faltantes": chaves_faltantes,
        }

    corrigido: dict[str, float] = {}
    for chave in CHAVES_TELEMETRIA:
        try:
            valor = float(dados[chave])
        except (TypeError, ValueError):
            return {
                "valido": False,
                "motivo": f"Valor invalido em {chave}.",
                "telemetria": None,
                "chaves_recebidas": chaves_recebidas,
                "chaves_faltantes": [],
            }
        minimo, maximo = LIMITES[chave]
        corrigido[chave] = round(max(minimo, min(maximo, valor)), 2)
    return {
        "valido": True,
        "motivo": "JSON validado.",
        "telemetria": corrigido,
        "chaves_recebidas": chaves_recebidas,
        "chaves_faltantes": [],
    }


def consultar_modelo_local(
    prompt: str,
    modelo: str = MODELO_PADRAO_OLLAMA,
    timeout_s: float = TIMEOUT_TELEMETRIA_IA,
    num_predict: int = 220,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": num_predict},
            "keep_alive": "10m",
        }
    ).encode("utf-8")
    requisicao = urllib.request.Request(URL_OLLAMA, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout_s) as resposta:
            corpo_bruto = resposta.read().decode("utf-8", errors="replace")
            corpo = json.loads(corpo_bruto)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
        tempo = time.perf_counter() - inicio
        return {
            "ok": False,
            "motivo": _resumir_erro_tecnico(erro),
            "texto": "",
            "texto_bruto": "",
            "corpo_bruto": "",
            "tempo_resposta_s": round(tempo, 3),
            "modelo": modelo,
            "timeout_usado": timeout_s,
            "url": URL_OLLAMA,
        }
    tempo = time.perf_counter() - inicio
    texto = str(corpo.get("response", ""))
    return {
        "ok": True,
        "motivo": "Resposta recebida do modelo local.",
        "texto": texto,
        "texto_bruto": texto,
        "corpo_bruto": corpo_bruto,
        "tempo_resposta_s": round(tempo, 3),
        "modelo": modelo,
        "timeout_usado": timeout_s,
        "url": URL_OLLAMA,
    }


def gerar_prompt_telemetria(config: Any, atualizacao: int, fallback: dict[str, float]) -> str:
    return (
        "Responda SOMENTE com um objeto JSON.\n"
        "Nao use markdown.\n"
        "Nao explique.\n\n"
        "Gere uma leitura de telemetria simulada usando exatamente estas chaves numericas:\n"
        "temperatura_interna, comunicacao_base, bateria, oxigenio, estabilidade_operacional,\n"
        "geracao_solar, consumo_suporte_vida, consumo_comunicacao, consumo_estabilidade,\n"
        "consumo_pesquisa, latencia_comunicacao_ms, perda_pacotes_percentual.\n\n"
        f"Use estes valores como referencia e varie pouco:\n{json.dumps(fallback, ensure_ascii=False)}\n\n"
        "Contexto:\n"
        f"Missao: {config.nome_missao}\n"
        f"Perfil: {config.perfil_risco}\n"
        f"Atualizacao: {atualizacao}/{config.total_atualizacoes}\n\n"
        "Retorne apenas o JSON."
    )


def aquecer_modelo_ollama(modelo: str = MODELO_PADRAO_OLLAMA, timeout_s: float = TIMEOUT_ANALISE_IA) -> dict[str, Any]:
    prompt = 'Responda apenas JSON: {"ok": true}'
    consulta = consultar_modelo_local(prompt, modelo=modelo, timeout_s=timeout_s, num_predict=40)
    if not consulta["ok"]:
        return {"ok": False, "motivo": consulta["motivo"], "modelo": modelo}
    try:
        dados = json.loads(consulta["texto"])
    except json.JSONDecodeError:
        return {"ok": False, "motivo": "O aquecimento retornou um texto inválido.", "modelo": modelo}
    return {"ok": bool(dados.get("ok")), "motivo": "Modelo aquecido." if dados.get("ok") else "Aquecimento sem confirmação.", "modelo": modelo}


def diagnosticar_geracao_telemetria_ia(
    config: Any,
    atualizacao: int,
    fallback: dict[str, float],
    timeout_s: float | None = None,
) -> dict[str, Any]:
    timeout_usado = timeout_s or getattr(config, "timeout_telemetria_ia", TIMEOUT_TELEMETRIA_IA)
    prompt = gerar_prompt_telemetria(config, atualizacao, fallback)
    consulta = consultar_modelo_local(prompt, timeout_s=timeout_usado, num_predict=220)
    if consulta["ok"]:
        validacao = validar_telemetria_ia(consulta["texto"])
    else:
        validacao = {
            "valido": False,
            "motivo": consulta["motivo"],
            "telemetria": None,
            "chaves_recebidas": [],
            "chaves_faltantes": CHAVES_TELEMETRIA,
        }
    origem_final = "ia + regras" if consulta["ok"] and validacao["valido"] else "fallback deterministico" if consulta["ok"] else "regras internas"
    return {
        "prompt": prompt,
        "modelo_usado": consulta.get("modelo", MODELO_PADRAO_OLLAMA),
        "timeout_usado": consulta.get("timeout_usado", timeout_usado),
        "tempo_resposta_s": consulta.get("tempo_resposta_s", 0),
        "url": consulta.get("url", URL_OLLAMA),
        "consulta_ok": consulta["ok"],
        "texto_bruto": consulta.get("texto_bruto", consulta.get("texto", "")),
        "corpo_bruto": consulta.get("corpo_bruto", ""),
        "validacao_ok": validacao["valido"],
        "motivo_validacao": validacao["motivo"],
        "chaves_recebidas": validacao.get("chaves_recebidas", []),
        "chaves_faltantes": validacao.get("chaves_faltantes", []),
        "origem_final": origem_final,
        "telemetria_validada": validacao.get("telemetria"),
    }


def gerar_telemetria_ia_com_fallback(
    config: Any,
    atualizacao: int,
    fallback: dict[str, float],
    timeout_s: float | None = None,
) -> dict[str, Any]:
    diagnostico = diagnosticar_geracao_telemetria_ia(config, atualizacao, fallback, timeout_s)
    if not diagnostico["consulta_ok"]:
        return {
            "telemetria": fallback,
            "origem": "regras internas",
            "validacao": diagnostico["motivo_validacao"],
            "json_bruto": "",
            "modelo": MODELO_PADRAO_OLLAMA,
            "erro_tecnico": diagnostico["motivo_validacao"],
            "diagnostico": diagnostico,
        }
    if not diagnostico["validacao_ok"]:
        return {
            "telemetria": fallback,
            "origem": "fallback deterministico",
            "validacao": diagnostico["motivo_validacao"],
            "json_bruto": diagnostico["texto_bruto"],
            "modelo": MODELO_PADRAO_OLLAMA,
            "erro_tecnico": diagnostico["motivo_validacao"],
            "diagnostico": diagnostico,
        }
    return {
        "telemetria": diagnostico["telemetria_validada"],
        "origem": "ia + regras",
        "validacao": diagnostico["motivo_validacao"],
        "json_bruto": diagnostico["texto_bruto"],
        "modelo": MODELO_PADRAO_OLLAMA,
        "erro_tecnico": "",
        "diagnostico": diagnostico,
    }


def gerar_contexto_analise_missao(estado_missao: Any) -> dict[str, Any]:
    telemetria = estado_missao.historico_telemetria[-1] if estado_missao.historico_telemetria else {}
    energia = estado_missao.historico_energia[-1] if estado_missao.historico_energia else {}
    risco = estado_missao.historico_risco[-1] if estado_missao.historico_risco else {"pontuacao": 0, "status": "NOMINAL"}
    principal_alerta = estado_missao.alertas_ativos[0]["mensagem"] if estado_missao.alertas_ativos else "Sem alerta ativo."
    eventos_criticos = [
        {
            "tempo": evento.get("tempo_missao"),
            "severidade": evento.get("severidade"),
            "sistema": evento.get("sistema"),
            "mensagem": evento.get("mensagem"),
        }
        for evento in estado_missao.historico_eventos[-8:]
        if evento["severidade"] == "CRITICO"
    ][-2:]
    return {
        "nome_missao": estado_missao.configuracao.nome_missao,
        "atualizacao_atual": estado_missao.atualizacao_atual,
        "total_atualizacoes": estado_missao.total_atualizacoes,
        "status_geral": estado_missao.status_geral,
        "risco_atual": risco["pontuacao"],
        "telemetria_atual": {
            "temperatura": telemetria.get("temperatura_interna"),
            "comunicacao": telemetria.get("comunicacao_base"),
            "bateria": telemetria.get("bateria"),
            "oxigenio": telemetria.get("oxigenio"),
            "estabilidade": telemetria.get("estabilidade_operacional"),
            "latencia": telemetria.get("latencia_comunicacao_ms"),
            "perda_pacotes": telemetria.get("perda_pacotes_percentual"),
        },
        "estado_energetico": {
            "status": energia.get("status"),
            "modo": energia.get("modo_energetico"),
            "saldo_energia": energia.get("saldo_energia", 0),
            "autonomia_horas": energia.get("autonomia_horas", 0),
        },
        "comunicacao": {
            chave: estado_missao.analise_comunicacao_atual().get(chave)
            for chave in ("status", "qualidade", "latencia", "perda", "estacao")
        },
        "principal_alerta": principal_alerta,
        "eventos_criticos_recentes": eventos_criticos,
        "recomendacoes_deterministicas": estado_missao.recomendacoes_prioritarias()[:2],
    }


def gerar_prompt_analise_missao(estado_missao: Any) -> str:
    contexto = gerar_contexto_analise_missao(estado_missao)
    return (
        f"{SYSTEM_PROMPT_ANALISE}\n"
        "Responda somente um objeto JSON, sem markdown e sem texto extra.\n"
        "Use exatamente estas chaves em minusculo: "
        f"{', '.join(CHAVES_ANALISE)}.\n"
        "Todos os valores devem ser strings curtas.\n"
        f"{INSTRUCAO_ANALISE}\n"
        f"Dados: {json.dumps(contexto, ensure_ascii=False, separators=(',', ':'))}"
    )


def consultar_ia_para_analise(
    prompt: str,
    modelo: str = MODELO_PADRAO_OLLAMA,
    timeout_s: float = TIMEOUT_ANALISE_IA,
) -> dict[str, Any]:
    return consultar_modelo_local(prompt, modelo=modelo, timeout_s=timeout_s, num_predict=180)


def validar_resposta_analise_ia(resposta: str) -> dict[str, Any]:
    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError:
        return {"valido": False, "motivo": "A resposta da IA para análise não está em JSON.", "analise": None}
    if not isinstance(dados, dict):
        return {"valido": False, "motivo": "A análise da IA deve ser um objeto JSON.", "analise": None}
    dados_normalizados = {str(chave).lower().strip(): valor for chave, valor in dados.items()}
    analise: dict[str, str] = {}
    obrigatorias = ["resumo", "principal_risco", "justificativa", "prioridade_operacional"]
    for chave in obrigatorias:
        valor = dados_normalizados.get(chave, "")
        texto = str(valor).strip()
        if not texto:
            return {"valido": False, "motivo": f"Campo ausente ou inválido: {chave}.", "analise": None}
        analise[chave] = texto
    proxima_acao = (
        dados_normalizados.get("proxima_acao")
        or dados_normalizados.get("acao_recomendada")
        or dados_normalizados.get("prioridade_operacional")
    )
    analise["proxima_acao"] = str(proxima_acao).strip()
    analise["nivel_confianca"] = str(dados_normalizados.get("nivel_confianca") or "medio").strip()
    analise["observacao"] = str(
        dados_normalizados.get("observacao") or "Análise complementar gerada a partir dos dados calculados pelo sistema."
    ).strip()
    return {"valido": True, "motivo": "Análise da IA validada.", "analise": analise}


def _analise_deterministica(contexto: dict[str, Any], origem: str, erro_tecnico: str = "") -> dict[str, str]:
    status = contexto.get("status_geral", "NOMINAL")
    risco = contexto.get("risco_atual", 0)
    energia = contexto.get("energia", {})
    comunicacao = contexto.get("comunicacao", {})
    principal_alerta = contexto.get("principal_alerta", "Sem alerta ativo.")
    recomendacoes = contexto.get("recomendacoes", [])

    resumo = f"Missão em status {status}, com risco atual {risco}."
    principal_risco = principal_alerta
    justificativa = (
        f"Energia em modo {energia.get('modo_energetico', 'sem dados')} "
        f"e comunicação {comunicacao.get('status', 'sem dados')}."
    )
    proxima_acao = recomendacoes[0] if recomendacoes else "Manter o monitoramento contínuo."

    return {
        "origem": origem,
        "modelo": MODELO_PADRAO_OLLAMA,
        "fallback_usado": "sim",
        "erro_tecnico": erro_tecnico,
        "resumo": resumo,
        "principal_risco": principal_risco,
        "justificativa": justificativa,
        "prioridade_operacional": proxima_acao,
        "proxima_acao": proxima_acao,
        "nivel_confianca": "medio",
        "observacao": "A IA interpreta os dados calculados pelo sistema e não substitui os cálculos determinísticos.",
        "recomendacao": proxima_acao,
        "prompt": "",
    }


def analisar_com_fallback(contexto: dict[str, Any], usar_ia: bool = False) -> dict[str, str]:
    resposta = _analise_deterministica(contexto, "modo deterministico")
    if not usar_ia:
        return resposta
    resposta["origem"] = "ia indisponivel - fallback deterministico"
    resposta["observacao"] = "Modo IA + regras preparado. Sem modelo conectado, o Python usa fallback validado."
    return resposta


def analisar_missao_com_ia(estado_missao: Any, usar_ia: bool = True, timeout_s: float | None = None) -> dict[str, str]:
    contexto = gerar_contexto_analise_missao(estado_missao)
    timeout_usado = timeout_s or getattr(estado_missao.configuracao, "timeout_analise_ia", TIMEOUT_ANALISE_IA)
    contexto_serializado = json.dumps(contexto, ensure_ascii=False, indent=2)
    configuracao_tecnica = json.dumps(
        {
            "modelo": MODELO_PADRAO_OLLAMA,
            "timeout": timeout_usado,
            "tipo_chamada": "analise operacional da missao",
            "atualizacao": contexto["atualizacao_atual"],
        },
        ensure_ascii=False,
        indent=2,
    )
    contexto_fallback = {
        "status_geral": contexto["status_geral"],
        "risco_atual": contexto["risco_atual"],
        "energia": contexto["estado_energetico"],
        "comunicacao": contexto["comunicacao"],
        "principal_alerta": contexto["principal_alerta"],
        "recomendacoes": contexto["recomendacoes_deterministicas"],
    }
    if not usar_ia:
        resposta = _analise_deterministica(contexto_fallback, "modo deterministico")
        resposta.update(
            {
                "prompt": "",
                "system_prompt": SYSTEM_PROMPT_ANALISE,
                "instrucao_principal": INSTRUCAO_ANALISE,
                "contexto_ia": contexto_serializado,
                "configuracao_tecnica": configuracao_tecnica,
                "resposta_bruta": "",
                "tempo_resposta_s": "0",
                "timeout_usado": str(timeout_usado),
            }
        )
        return resposta

    prompt = gerar_prompt_analise_missao(estado_missao)
    metadados = {
        "prompt": prompt,
        "system_prompt": SYSTEM_PROMPT_ANALISE,
        "instrucao_principal": INSTRUCAO_ANALISE,
        "contexto_ia": contexto_serializado,
        "configuracao_tecnica": configuracao_tecnica,
        "timeout_usado": str(timeout_usado),
    }
    consulta = consultar_ia_para_analise(prompt, timeout_s=timeout_usado)
    if not consulta["ok"]:
        resposta = _analise_deterministica(contexto_fallback, "ia indisponivel - fallback deterministico", consulta["motivo"])
        resposta.update(metadados)
        resposta["resposta_bruta"] = consulta.get("texto_bruto", consulta.get("texto", ""))
        resposta["tempo_resposta_s"] = str(consulta.get("tempo_resposta_s", 0))
        return resposta

    validacao = validar_resposta_analise_ia(consulta["texto"])
    if not validacao["valido"]:
        resposta = _analise_deterministica(contexto_fallback, "fallback deterministico", validacao["motivo"])
        resposta.update(metadados)
        resposta["resposta_bruta"] = consulta.get("texto_bruto", consulta.get("texto", ""))
        resposta["tempo_resposta_s"] = str(consulta.get("tempo_resposta_s", 0))
        return resposta

    analise = validacao["analise"]
    analise.update(
        {
            "origem": "IA",
            "modelo": MODELO_PADRAO_OLLAMA,
            "fallback_usado": "nao",
            "erro_tecnico": "",
            "recomendacao": analise["proxima_acao"],
            "resposta_bruta": consulta.get("texto_bruto", consulta.get("texto", "")),
            "tempo_resposta_s": str(consulta.get("tempo_resposta_s", 0)),
        }
    )
    analise.update(metadados)
    return analise
