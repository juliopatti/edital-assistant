"""
Utilitários compartilhados pelos notebooks do estudos_integrados_v3.

Mudanças em relação à v2:
    - Provedor "Claude" renomeado para "Anthropic" (paridade com "OpenAI").
    - Estudo focado em 4 dimensões: precisão, concisão, latência, custo.
    - Convenção visual reforçada: API = bolinha (o), Chat web = quadrado (s).
    - Helpers para comparações pareadas (Chat vs API do mesmo provedor)
      e agrupadas (todos os modelos lado a lado por dimensão).
    - Função `anota_sem_sobrepor` que usa adjustText quando disponível
      e cai num fallback manual caso contrário.
    - `agrega_por_modelo()` devolve a tabela mestre já no formato usado
      em todos os scatters/plots.
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
    "gpt-4o-mini":        "GPT-4o mini",
    "gpt-5.4":            "GPT-5.4",
    "gpt-5.4-mini":       "GPT-5.4 mini",
    "gpt-5.5":            "GPT-5.5",
    "std_chatgpt":        "ChatGPT (chat web)",
    "std_claude":         "Claude (chat web)",
}

# Provedor (antigo "familia"). Renomeado para "Anthropic" em vez de "Claude".
PROVEDOR = {
    "claude-haiku-4-5":   "Anthropic",
    "claude-opus-4-7":    "Anthropic",
    "claude-sonnet-4-6":  "Anthropic",
    "deepseek-v4-flash":  "DeepSeek",
    "deepseek-v4-pro":    "DeepSeek",
    "gpt-4o-mini":        "OpenAI",
    "gpt-5.4":            "OpenAI",
    "gpt-5.4-mini":       "OpenAI",
    "gpt-5.5":            "OpenAI",
    "std_chatgpt":        "OpenAI",
    "std_claude":         "Anthropic",
}

# Paleta por provedor: tons saturados, distintos, com bom contraste em fundo branco.
CORES_PROVEDOR = {
    "OpenAI":   "#10A37F",   # verde institucional
    "Anthropic": "#D97757",  # laranja terracota
    "DeepSeek": "#4D6BFE",   # azul royal
}

# Variantes claras (para fundo de fills, bandas, etc.)
CORES_PROVEDOR_CLARO = {
    "OpenAI":   "#A8D9C6",
    "Anthropic": "#F0BFA8",
    "DeepSeek": "#B6C2FE",
}

# Ordem padrão de exibição de modelos (provedor agrupado, API antes do chat web)
ORDEM_MODELOS = [
    "GPT-4o mini", "GPT-5.4 mini", "GPT-5.4", "GPT-5.5",
    "Claude Haiku 4.5", "Claude Sonnet 4.6", "Claude Opus 4.7",
    "DeepSeek v4 Flash", "DeepSeek v4 Pro",
    "ChatGPT (chat web)", "Claude (chat web)",
]

# Pares Chat web <-> API mais alta do mesmo provedor (para comparações pareadas)
PARES_CHAT_API = [
    ("ChatGPT (chat web)", "GPT-5.5"),
    ("Claude (chat web)",  "Claude Opus 4.7"),
]

# Marcadores: convenção fixa do estudo.
MARKER_API = "o"
MARKER_CHAT = "s"

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
    df["provedor"]       = df["modelo"].map(PROVEDOR)
    df["cor"]            = df["provedor"].map(CORES_PROVEDOR)

    # Convenção visual: API = bolinha, Chat web = quadrado
    df["marker"] = df["origem_resultado"].map(
        {"ferramenta": MARKER_API, "chat_comercial": MARKER_CHAT}
    )

    # Origem em rótulo amigável
    df["origem"] = df["origem_resultado"].map(
        {"ferramenta": "API", "chat_comercial": "Chat web"}
    )

    # Tokens de fluxo interno (raciocínio + chamadas de ferramenta).
    # Só faz sentido para API (chat web não expõe esse número).
    df["tokens_fluxo_interno"] = df["output_tokens"] - df["resposta_tokens_tiktoken"]

    return df


def agrega_por_modelo(df):
    """Tabela mestre: uma linha por modelo, todas as métricas necessárias.

    Esta é a base de todos os scatters comparativos do estudo. Já entrega
    na ORDEM_MODELOS para que os gráficos saiam previsíveis.
    """
    def media_safe(s):
        return s.mean() if s.notna().any() else np.nan

    mestre = (df.groupby("modelo_display")
                .agg(precisao   = ("avaliacao_final",          "mean"),
                     concisao   = ("concisao_score",           "mean"),
                     tokens_resp= ("resposta_tokens_tiktoken", "mean"),
                     latencia_s = ("latencia_s",               media_safe),
                     custo_usd  = ("custo_estimado_usd",       media_safe),
                     n          = ("id",                       "count"),
                     provedor   = ("provedor",                 "first"),
                     origem     = ("origem",                   "first"))
                .loc[ORDEM_MODELOS]
                .copy())
    mestre["cor"]    = mestre["provedor"].map(CORES_PROVEDOR)
    mestre["marker"] = mestre["origem"].map({"API": MARKER_API, "Chat web": MARKER_CHAT})
    return mestre


# -----------------------------------------------------------------------------
# Estilo
# -----------------------------------------------------------------------------
def estilo_padrao():
    """rcParams consistentes em todos os notebooks."""
    plt.rcParams.update({
        "figure.facecolor":      "white",
        "axes.facecolor":        "white",
        "axes.spines.top":       False,
        "axes.spines.right":     False,
        "axes.grid":             True,
        "grid.alpha":            0.22,
        "grid.linestyle":        "--",
        "grid.linewidth":        0.6,
        "font.size":             10,
        "axes.titlesize":        12,
        "axes.titleweight":      "bold",
        "axes.titlepad":         14,
        "axes.titlelocation":    "left",
        "axes.labelsize":        10,
        "axes.labelcolor":       "#222",
        "xtick.color":           "#444",
        "ytick.color":           "#444",
        "legend.frameon":        False,
        "legend.fontsize":       9,
        "figure.dpi":            110,
        "savefig.dpi":           160,
        "savefig.bbox":          "tight",
    })


# -----------------------------------------------------------------------------
# Helpers de plotagem
# -----------------------------------------------------------------------------
def titulo_acima(ax, titulo, subtitulo=None, y_titulo=1.13, y_subtitulo=1.04):
    """Título em negrito + subtítulo opcional acima do eixo, sem sobreposição."""
    ax.set_title("")
    if subtitulo:
        ax.text(0.0, y_titulo, titulo, transform=ax.transAxes,
                fontsize=12, fontweight="bold", ha="left", va="bottom")
        ax.text(0.0, y_subtitulo, subtitulo, transform=ax.transAxes,
                fontsize=9.5, color="#555", ha="left", va="bottom")
    else:
        ax.text(0.0, y_subtitulo, titulo, transform=ax.transAxes,
                fontsize=12, fontweight="bold", ha="left", va="bottom")


def anota_sem_sobrepor(ax, xs, ys, labels, *, fontsize=9, color="#222",
                       force_text=(0.6, 1.2), force_points=(0.4, 0.6),
                       expand=(1.4, 1.8), usar_adjust=False,
                       offsets_manuais=None):
    """Rotula pontos com posicionamento manual editável.

    O default usa `offsets_manuais` (dict label -> (dx_pt, dy_pt)), porque
    em um TCC quem está revisando o gráfico quer poder mover o rótulo de
    um modelo específico sem disputa com um algoritmo. Isso significa que
    cada chamada nos notebooks declara explicitamente onde cada rótulo
    deve ficar — e você edita ali no código quando quiser.

    Se preferir delegar ao `adjustText`, passe `usar_adjust=True`. Os
    parâmetros `force_text`, `force_points` e `expand` são repassados.

    Sem entrada em `offsets_manuais`, o rótulo cai 9pt acima do ponto.
    """
    offsets_manuais = offsets_manuais or {}
    if usar_adjust:
        try:
            from adjustText import adjust_text
            texts = [ax.text(xi, yi, lab, fontsize=fontsize, color=color, alpha=0.95)
                     for xi, yi, lab in zip(xs, ys, labels)]
            adjust_text(
                texts, ax=ax,
                arrowprops=dict(arrowstyle="-", color="#888", lw=0.5, alpha=0.55),
                force_text=force_text, force_points=force_points,
                expand=expand,
                only_move={"text": "xy", "static": "xy", "explode": "xy"},
            )
            return
        except ImportError:
            pass
    for xi, yi, lab in zip(xs, ys, labels):
        dx, dy = offsets_manuais.get(lab, (0, 9))
        ha = "center" if dx == 0 else ("left" if dx > 0 else "right")
        va = "bottom" if dy >= 0 else "top"
        ax.annotate(lab, xy=(xi, yi), xytext=(dx, dy),
                    textcoords="offset points",
                    ha=ha, va=va, fontsize=fontsize, color=color)


def bootstrap_ic(serie, n_boot=2000, ci=0.95, seed=42):
    """IC bootstrap simples para a média."""
    rng = np.random.default_rng(seed)
    valores = np.asarray(serie.dropna())
    if len(valores) == 0:
        return (np.nan, np.nan)
    medias = rng.choice(valores, size=(n_boot, len(valores)), replace=True).mean(axis=1)
    lo = np.quantile(medias, (1 - ci) / 2)
    hi = np.quantile(medias, 1 - (1 - ci) / 2)
    return (lo, hi)


def normalizar_minmax(s, invertir=False):
    """Normalização min-max para [0, 1]. `invertir=True` quando 'menor é melhor'."""
    s = pd.Series(s).astype(float)
    smin, smax = s.min(), s.max()
    if smax == smin:
        return pd.Series([0.5] * len(s), index=s.index)
    norm = (s - smin) / (smax - smin)
    return 1 - norm if invertir else norm


# -----------------------------------------------------------------------------
# Helpers de comparação pareada
# -----------------------------------------------------------------------------
def plot_barras_pareadas(ax, mestre, coluna, *, titulo_y="",
                         valor_fmt=lambda v: f"{v:.2f}", ordem=None,
                         destaque_chat=True):
    """Barras agrupadas — uma barra por modelo, cor por provedor, hatch para Chat web.

    A ordem default é ORDEM_MODELOS, mas pode ser sobrescrita.
    """
    ordem = ordem or ORDEM_MODELOS
    sub = mestre.loc[ordem]
    xs = np.arange(len(sub))
    cores = sub["cor"].tolist()
    hatch = ["///" if o == "Chat web" else None for o in sub["origem"]]

    bars = ax.bar(xs, sub[coluna].values, color=cores, edgecolor="#222",
                  linewidth=0.7, width=0.72)
    for b, h in zip(bars, hatch):
        if h:
            b.set_hatch(h)

    ax.set_xticks(xs)
    ax.set_xticklabels(sub.index, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel(titulo_y)

    # rótulo no topo da barra
    for x, v in zip(xs, sub[coluna].values):
        if pd.notna(v):
            ax.text(x, v, " " + valor_fmt(v), ha="center", va="bottom",
                    fontsize=8.5, color="#333", rotation=0)

    # separadores verticais entre provedores
    fronteiras = []
    last = None
    for i, p in enumerate(sub["provedor"]):
        if last is not None and p != last:
            fronteiras.append(i - 0.5)
        last = p
    for f in fronteiras:
        ax.axvline(f, color="#ddd", lw=0.6, zorder=0)

    return bars


def legenda_provedor_origem(ax, loc="upper right"):
    """Legenda compacta que explica cores (provedor) e marcadores (origem)."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=CORES_PROVEDOR["OpenAI"],   edgecolor="#222", label="OpenAI"),
        Patch(facecolor=CORES_PROVEDOR["Anthropic"], edgecolor="#222", label="Anthropic"),
        Patch(facecolor=CORES_PROVEDOR["DeepSeek"], edgecolor="#222", label="DeepSeek"),
        Line2D([0], [0], marker=MARKER_API,  color="w", markerfacecolor="#999",
               markeredgecolor="#222", markersize=9, label="API"),
        Line2D([0], [0], marker=MARKER_CHAT, color="w", markerfacecolor="#999",
               markeredgecolor="#222", markersize=9, label="Chat web"),
    ]
    ax.legend(handles=handles, loc=loc, ncol=1, fontsize=8.5,
              handletextpad=0.6, labelspacing=0.5)
