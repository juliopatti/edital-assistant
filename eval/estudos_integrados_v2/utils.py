"""
Utilitários compartilhados pelos notebooks do estudos_integrados_v2.

- carregar_dados(): leitura única do result_unificado_final.xlsx, com
  padronização de nomes de modelo, família e conversão numérica das
  colunas que vêm como "nao pertinente" nos chats comerciais.
- estilo_padrao(): rcParams matplotlib consistentes em todos os notebooks.
- helpers de plotagem: rotulos_em_cima(), titulo_acima(), bootstrap_ic().
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# Caminhos
# -----------------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "data" / "result_unificado_final.xlsx"

# -----------------------------------------------------------------------------
# Padronização de nomes
# -----------------------------------------------------------------------------
MODELO_DISPLAY = {
    "claude-haiku-4-5":   "Claude Haiku 4.5",
    "claude-opus-4-7":    "Claude Opus 4.7",
    "claude-sonnet-4-6":  "Claude Sonnet 4.6",
    "deepseek-v4-flash":  "DeepSeek v4 Flash",
    "deepseek-v4-pro":    "DeepSeek v4 Pro",
    "gpt-4o-mini":    "GPT-4o mini", 
    "gpt-5.4":        "GPT-5.4",        
    "gpt-5.4-mini":   "GPT-5.4 mini",    
    "gpt-5.5":        "GPT-5.5",     
    "std_chatgpt":    "ChatGPT (chat web)",
    "std_claude":         "Claude (chat web)",
}

FAMILIA = {
    "claude-haiku-4-5":  "Claude",  "claude-opus-4-7":   "Claude",  "claude-sonnet-4-6": "Claude",
    "deepseek-v4-flash": "DeepSeek", "deepseek-v4-pro":  "DeepSeek",
    "gpt-4o-mini":  "OpenAI",  "gpt-5.4":    "OpenAI",
    "gpt-5.4-mini": "OpenAI",  "gpt-5.5":    "OpenAI",
    "std_chatgpt":  "OpenAI", "std_claude":        "Claude",
}

CORES_FAMILIA = {"OpenAI": "#10A37F", "Claude": "#D97757", "DeepSeek": "#4D6BFE"} 

# Ordem padrão de exibição de modelos (família agrupada, ferramenta antes do chat web)
ORDEM_MODELOS = [
    "GPT-4o mini", "GPT-5.4 mini", "GPT-5.4", "GPT-5.5", 
    "Claude Haiku 4.5", "Claude Sonnet 4.6", "Claude Opus 4.7",
    "DeepSeek v4 Flash", "DeepSeek v4 Pro",
    "ChatGPT (chat web)", "Claude (chat web)",
]

# -----------------------------------------------------------------------------
# Carregamento
# -----------------------------------------------------------------------------
def carregar_dados():
    """Carrega o xlsx unificado e devolve um DataFrame pronto para análise."""
    df = pd.read_excel(DATA_PATH)

    # Colunas que vêm como string "nao pertinente" nas linhas de chat web:
    # forçamos para numérico (vira NaN nas linhas sem ferramenta).
    for c in ["input_tokens", "output_tokens", "n_invocacoes",
              "latencia_s", "custo_estimado_usd"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["modelo_display"] = df["modelo"].map(MODELO_DISPLAY)
    df["familia"]        = df["modelo"].map(FAMILIA)
    df["cor"]            = df["familia"].map(CORES_FAMILIA)

    # Marcadores: ferramenta = bolinha, chat web = quadrado
    df["marker"] = df["origem_resultado"].map(
        {"ferramenta": "o", "chat_comercial": "s"}
    )

    # Tokens de fluxo interno (raciocínio + chamadas de ferramenta).
    # Só faz sentido para ferramenta (chat web não expõe esse número).
    df["tokens_fluxo_interno"] = df["output_tokens"] - df["resposta_tokens_tiktoken"]

    return df


# -----------------------------------------------------------------------------
# Estilo
# -----------------------------------------------------------------------------
def estilo_padrao():
    """Aplica rcParams consistentes a todos os notebooks."""
    plt.rcParams.update({
        "figure.facecolor":      "white",
        "axes.facecolor":        "white",
        "axes.spines.top":       False,
        "axes.spines.right":     False,
        "axes.grid":             True,
        "grid.alpha":            0.25,
        "grid.linestyle":        "--",
        "font.size":             10,
        "axes.titlesize":        12,
        "axes.titleweight":      "bold",
        "axes.titlepad":         14,
        "axes.titlelocation":    "left",
        "axes.labelsize":        10,
        "legend.frameon":        False,
        "legend.fontsize":       9,
        "figure.dpi":            100,
    })


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def titulo_acima(ax, titulo, subtitulo=None):
    """Coloca título principal (em negrito) e subtítulo opcional acima do eixo.

    O título vai num y mais alto e o subtítulo logo abaixo, ambos via ax.text
    para garantir que nenhum se sobreponha ao outro mesmo com axes.titlepad.
    """
    # Desliga qualquer título nativo para não conflitar
    ax.set_title("")
    if subtitulo:
        # Título mais alto + subtítulo logo abaixo
        ax.text(0.0, 1.13, titulo, transform=ax.transAxes,
                fontsize=12, fontweight="bold", ha="left", va="bottom")
        ax.text(0.0, 1.04, subtitulo, transform=ax.transAxes,
                fontsize=9.5, color="#555", ha="left", va="bottom")
    else:
        ax.text(0.0, 1.04, titulo, transform=ax.transAxes,
                fontsize=12, fontweight="bold", ha="left", va="bottom")


def rotulos_em_cima(ax, xs, ys, labels, dy=0.012, dx=0, fontsize=8.5, color="#222",
                    offsets=None):
    """Rotula cada ponto acima de sua posição.

    `offsets` (opcional): dict {label: (dx_pt, dy_pt)} para deslocar rótulos
    específicos quando estiverem se sobrepondo.
    """
    offsets = offsets or {}
    for x, y, lab in zip(xs, ys, labels):
        dxp, dyp = offsets.get(lab, (dx, 8))
        ax.annotate(lab, xy=(x, y), xytext=(dxp, dyp),
                    textcoords="offset points",
                    ha="center", va="bottom",
                    fontsize=fontsize, color=color)


def bootstrap_ic(serie, n_boot=2000, ci=0.95, seed=42):
    """IC bootstrap simples para a média. Sem Wilson, sem firula."""
    rng = np.random.default_rng(seed)
    valores = np.asarray(serie.dropna())
    if len(valores) == 0:
        return (np.nan, np.nan)
    medias = rng.choice(valores, size=(n_boot, len(valores)), replace=True).mean(axis=1)
    lo = np.quantile(medias, (1 - ci) / 2)
    hi = np.quantile(medias, 1 - (1 - ci) / 2)
    return (lo, hi)


def normalizar_minmax(s):
    """Normalização min-max para [0, 1]. NaN-safe."""
    s = pd.Series(s).astype(float)
    smin, smax = s.min(), s.max()
    if smax == smin:
        return pd.Series([0.5] * len(s), index=s.index)
    return (s - smin) / (smax - smin)
