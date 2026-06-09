# Mission Control AI

Sistema Python para simular uma missão espacial com telemetria dinâmica, análise energética sustentável, eventos operacionais, painel Tkinter e apoio opcional de IA local via Ollama.

## Como executar

```bash
python main.py
```

O fluxo sempre abre a tela **Configuracao da Missao** primeiro. Depois de clicar em **Iniciar missao**, o dashboard principal abre com o `EstadoMissao` configurado.

## IA local com Ollama

O sistema usa IA de forma opcional. Sem Ollama ou sem modelo disponível, ele continua funcionando por regras internas e fallback determinístico.

Modelo padrão:

```text
llama3.2:1b
```

Variáveis de ambiente úteis:

```bash
MISSION_CONTROL_IA_MODELO=llama3.2:1b
MISSION_CONTROL_IA_TIMEOUT_STATUS=60.0
MISSION_CONTROL_IA_TIMEOUT_TELEMETRIA=60.0
MISSION_CONTROL_IA_TIMEOUT_ANALISE=60.0
MISSION_CONTROL_IA_TIMEOUT_RELATORIO=60.0
```

## Testes e diagnóstico

```bash
python -m unittest discover tests
python tests/diagnostico_ia.py
python tests/benchmark_ia.py
```

Compilação rápida:

```bash
python -m py_compile main.py
python -m py_compile sistema_integrado/*.py
```

No Windows, para compilar recursivamente as entregas individuais:

```powershell
Get-ChildItem entregas_materias -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## Estrutura

```text
Mission_Control_IA/
├── main.py
├── README.md
├── sistema_integrado/
├── entregas_materias/
└── tests/
```

`sistema_integrado/` contém o sistema final: configuração, estado da missão, geração de telemetria, motores de risco/energia/eventos, IA, relatório e interfaces.

`entregas_materias/` mantém os módulos individuais por disciplina, separados do sistema final.

`tests/` concentra testes, benchmark e diagnóstico de IA.

## Tempo simulado

A duração e o intervalo da missão são simulados. O campo **Segundos reais por atualizacao** define apenas a velocidade de execução visual. Exemplo: uma missão de 90 minutos com intervalo de 5 minutos tem 18 atualizações; se a escala real for 2 segundos, cada atualização visual ocorre a cada 2 segundos reais no modo automático.

## Papel da IA

A IA pode participar de duas formas:

- Geração de telemetria por atualização, validada por regras internas.
- Análise/recomendação ao operador a partir do estado já calculado.

A IA não substitui os motores determinísticos. Toda resposta é validada, e o fallback preserva a simulação quando o modelo demora, responde fora do formato ou está indisponível.

## Continuidade

Ao alterar o projeto:

- Preserve `main.py` como entrada principal.
- Não misture entregas individuais com o sistema integrado.
- Rode os testes antes e depois de mudanças.
- Mantenha a interface responsiva; chamadas de IA devem rodar fora do loop principal do Tkinter.
- Não remova fallbacks, validações ou arquivos usados pelos testes.
