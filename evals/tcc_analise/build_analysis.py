"""
Pipeline integrado do TCC.
Lê os 5 arquivos consolidados, faz todas as análises e exporta o Excel mestre.

Arquivos de entrada (em ./data/):
  - df_avaliacoes.xlsx           : 1.350 linhas, qualidade GPT+Opus para 9 modelos API
  - df_metricas.xlsx             : 2.700 linhas, métricas operacionais API
  - divergentes_human_eval.xlsx  : 92 casos divergentes API com árbitro humano
  - chats_div_avaliado.xlsx      : 29 casos divergentes chats com árbitro humano
  - analise_consolidada.xlsx     : 1.650 linhas, rubric unificado (correção+foco) p/ 11 modelos

Saída:
  - output/tcc_analise_integrada.xlsx  (Excel mestre, várias abas)
  - dataframes intermediários para uso pelos notebooks
"""
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy import stats

try:
    import tiktoken
    ENC = tiktoken.get_encoding('cl100k_base')
    def count_tokens(s):
        return 0 if not isinstance(s, str) or not s else len(ENC.encode(s))
    TOKENIZER = 'tiktoken/cl100k_base'
except Exception as e:
    def count_tokens(s):
        return 0 if not isinstance(s, str) or not s else int(round(len(s.split()) / 0.75))
    TOKENIZER = f'fallback/palavras ({type(e).__name__})'

DATA_CANDIDATOS = [Path('.'), Path('data'), Path('../data'), Path('./data')]
DATA = next((p.resolve() for p in DATA_CANDIDATOS
             if (p / 'df_avaliacoes.xlsx').exists()), None)
if DATA is None:
    raise FileNotFoundError(
        'Não encontrei df_avaliacoes.xlsx. Coloque os 5 .xlsx em ./data/ '
        'ou no mesmo diretório do script.'
    )
OUT  = (DATA.parent / 'output') if DATA.name == 'data' else (DATA / 'output')
OUT.mkdir(exist_ok=True)
print(f'DATA = {DATA}')
print(f'OUT  = {OUT}')

# Normalização: nomes diferentes entre arquivos para os chats
CHAT_NAME_MAP = {
    'std_chatgpt': 'chatgpt',
    'std_claude':  'claude_chat',
}

# ============================================================================
# BLOCO 1 — Carregamento e normalização
# ============================================================================
print('═' * 70)
print('BLOCO 1 — Carregamento')
print('═' * 70)

df_av  = pd.read_excel(DATA / 'df_avaliacoes.xlsx')
df_me  = pd.read_excel(DATA / 'df_metricas.xlsx')
df_div = pd.read_excel(DATA / 'divergentes_human_eval.xlsx')
df_chat_div = pd.read_excel(DATA / 'chats_div_avaliado.xlsx')
df_uni = pd.read_excel(DATA / 'analise_consolidada.xlsx')

# Normalizar nomes de chat para a coluna 'modelo' do df_chat_div
df_chat_div['modelo'] = df_chat_div['modelo'].replace(CHAT_NAME_MAP)

# Renomear colunas para alinhar com o padrão do estudo 1
df_chat_div = df_chat_div.rename(columns={
    'avaliação humana': 'avaliacao_humana',
    'modelo.1': 'modelo_correto',
})

print(f'df_avaliacoes (API):           {df_av.shape}')
print(f'df_metricas (API):             {df_me.shape}')
print(f'divergentes API (humano):      {df_div.shape}')
print(f'divergentes chats (humano):    {df_chat_div.shape}')
print(f'rubric unificado:              {df_uni.shape}')
print(f'Tokenizador:                   {TOKENIZER}')

# ============================================================================
# BLOCO 2 — Qualidade API: construir avaliacao_final com árbitro humano
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 2 — Qualidade dos 9 modelos API (avaliacao_final + Kappa)')
print('═' * 70)

# Extrair edital e modelo da coluna 'pasta' (formato 'edital_modelo')
df_div[['edital_h', 'modelo_h']] = df_div['pasta'].str.split('_', n=1, expand=True)
lookup_h = (df_div[['edital_h', 'modelo_h', 'id', 'Avaliação Humana', 'Modelo Correto']]
            .rename(columns={'edital_h': 'edital', 'modelo_h': 'modelo',
                             'Avaliação Humana': 'avaliacao_humana',
                             'Modelo Correto': 'modelo_correto'}))

df_av = df_av.merge(lookup_h, on=['edital', 'modelo', 'id'], how='left')

# avaliacao_final: consenso quando converge; humano quando diverge
df_av['avaliacao_final'] = np.where(
    df_av['convergencia'],
    df_av['avaliacao_gpt'],
    df_av['avaliacao_humana']
)
df_av['nota_consenso'] = (df_av['avaliacao_gpt'] + df_av['avaliacao_opus']) / 2

n_div = (~df_av['convergencia']).sum()
n_humano_aplicado = df_av[~df_av['convergencia'] & df_av['avaliacao_final'].notna()].shape[0]
print(f'Divergências API:                  {n_div}')
print(f'Com árbitro humano aplicado:       {n_humano_aplicado}')
print(f'Nulls em avaliacao_final:          {df_av["avaliacao_final"].isna().sum()}')

# Kappa GPT × Opus
gpt_int  = (df_av['avaliacao_gpt']  * 2).astype(int)
opus_int = (df_av['avaliacao_opus'] * 2).astype(int)
kappa_api = cohen_kappa_score(gpt_int, opus_int)
conv_api = df_av['convergencia'].mean()
print(f'Convergência GPT × Opus (API):     {conv_api:.1%}')
print(f"Cohen's Kappa (API):               {kappa_api:.3f}")

# ============================================================================
# BLOCO 3 — Métricas operacionais (latência, tokens, invocações)
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 3 — Métricas operacionais API')
print('═' * 70)

# Uma linha por pergunta/modelo (evita duplicar entre avaliadores)
df_op = df_me[df_me['avaliador'] == 'gpt'].copy()
print(f'Linhas operacionais (um avaliador): {len(df_op)}')

op_por_modelo = df_op.groupby(['modelo', 'provedor']).agg(
    latencia_mediana=('latencia_s', 'median'),
    latencia_media=('latencia_s', 'mean'),
    latencia_p90=('latencia_s', lambda x: x.quantile(0.9)),
    output_tokens_media=('output_tokens', 'mean'),
    input_tokens_media=('input_tokens', 'mean'),
    total_tokens_media=('total_tokens', 'mean'),
    cache_read_tokens_media=('cache_read_tokens', 'mean'),
    n_invocacoes_media=('n_invocacoes', 'mean'),
).round(2).reset_index()

# ============================================================================
# BLOCO 4 — Rubric unificado: enriquecer com tokens
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 4 — Tokens em todas as respostas (11 modelos)')
print('═' * 70)

n_nulas = df_uni['resposta'].isna().sum()
if n_nulas:
    print(f'AVISO: {n_nulas} respostas nulas no df_uni — contadas como 0 tokens')

df_uni['n_tokens'] = df_uni['resposta'].fillna('').astype(str).apply(count_tokens)
df_uni['n_palavras'] = df_uni['resposta'].fillna('').astype(str).str.split().str.len().fillna(0).astype(int)
df_uni['n_chars'] = df_uni['resposta'].fillna('').astype(str).str.len()

print(f'Tokens: min={df_uni.n_tokens.min()}, mediana={df_uni.n_tokens.median():.0f}, '
      f'média={df_uni.n_tokens.mean():.1f}, p90={df_uni.n_tokens.quantile(0.9):.0f}, '
      f'max={df_uni.n_tokens.max()}')

# Score "focado" (1.0) — taxa por modelo
def wilson_ci(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denom
    margem = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centro - margem, centro + margem)

# Tabela por modelo no rubric unificado
rubric_por_modelo = (
    df_uni.groupby(['modelo', 'tipo', 'provider'])
    .agg(
        score_medio=('score', 'mean'),
        score_mediano=('score', 'median'),
        n_perfeito=('score', lambda x: (x == 1.0).sum()),
        n_parcial=('score', lambda x: (x == 0.5).sum()),
        n_errado=('score', lambda x: (x == 0.0).sum()),
        tokens_media=('n_tokens', 'mean'),
        tokens_mediana=('n_tokens', 'median'),
        tokens_p90=('n_tokens', lambda x: x.quantile(0.9)),
        palavras_media=('n_palavras', 'mean'),
        n_total=('score', 'count'),
    )
    .reset_index()
    .sort_values('score_medio', ascending=False)
)
rubric_por_modelo['taxa_perfeita'] = rubric_por_modelo['n_perfeito'] / rubric_por_modelo['n_total']

# IC Wilson 95% para taxa_perfeita
icw = rubric_por_modelo.apply(
    lambda r: wilson_ci(int(r['n_perfeito']), int(r['n_total'])), axis=1)
rubric_por_modelo['ic_lo'] = [a for a, b in icw]
rubric_por_modelo['ic_hi'] = [b for a, b in icw]
rubric_por_modelo = rubric_por_modelo.round(4)

print(f'Score médio (top 5):')
print(rubric_por_modelo[['modelo', 'tipo', 'score_medio', 'taxa_perfeita', 'tokens_media']].head().to_string(index=False))

# ============================================================================
# BLOCO 5 — Ranking unificado: junta qualidade + métricas + concisão
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 5 — Ranking unificado (11 modelos)')
print('═' * 70)

# Qualidade API (avaliacao_final): só os 9 API
qual_api = df_av.groupby(['modelo', 'provedor']).agg(
    avaliacao_final=('avaliacao_final', 'mean'),
    nota_consenso=('nota_consenso', 'mean'),
    convergencia_gpt_opus=('convergencia', 'mean'),
    n_divergencias=('convergencia', lambda x: (~x).sum()),
).reset_index()

# Qualidade chats: só temos as 29 divergências humanas → calcular a posteriori
# Para "avaliacao_final dos chats", usamos o score do rubric unificado como proxy
# já que ele é a única medida que cobre os 300 chats consistentemente.
qual_chat = (df_uni[df_uni['tipo'] == 'chat']
             .groupby(['modelo', 'provider'])
             .agg(score_rubric=('score', 'mean'))
             .reset_index()
             .rename(columns={'provider': 'provedor'}))

# Score do rubric também para API (para todos os 11)
score_rubric_todos = (df_uni.groupby('modelo')['score'].mean()
                     .rename('score_rubric').reset_index())

# Tokens de saída (médio): de df_metricas para API, computado para chats
tokens_api = (df_op.groupby('modelo')['output_tokens'].mean()
             .rename('output_tokens_real').reset_index())
tokens_chat_proxy = (df_uni[df_uni['tipo'] == 'chat']
                    .groupby('modelo')['n_tokens'].mean()
                    .rename('output_tokens_real').reset_index())
tokens_todos = pd.concat([tokens_api, tokens_chat_proxy], ignore_index=True)

# Latência: só API
lat_api = (df_op.groupby('modelo')['latencia_s'].median()
          .rename('latencia_mediana').reset_index())

# Montar ranking unificado
ranking = qual_api.copy()
ranking['tipo'] = 'api'

# Adicionar chats com colunas faltantes como NaN
ranking_chat = qual_chat.copy()
ranking_chat['tipo'] = 'chat'
ranking_chat['avaliacao_final'] = np.nan      # não disponível para chats
ranking_chat['nota_consenso'] = np.nan
ranking_chat['convergencia_gpt_opus'] = np.nan
ranking_chat['n_divergencias'] = (df_chat_div.groupby('modelo')
                                  .size().reindex(ranking_chat['modelo']).fillna(0).values)
ranking_chat = ranking_chat[ranking.columns.tolist() + ['tipo'] if 'tipo' not in ranking_chat.columns else ranking_chat.columns.tolist()]

# Reordenar colunas do ranking_chat para bater com ranking
cols_pad = ['modelo', 'provedor', 'avaliacao_final', 'nota_consenso',
            'convergencia_gpt_opus', 'n_divergencias', 'tipo']
ranking = ranking[cols_pad]
ranking_chat = ranking_chat[cols_pad]
ranking = pd.concat([ranking, ranking_chat], ignore_index=True)

ranking = (ranking.merge(score_rubric_todos, on='modelo', how='left')
           .merge(tokens_todos, on='modelo', how='left')
           .merge(lat_api, on='modelo', how='left'))

# Ordenar por score_rubric (único campo que cobre todos)
ranking = ranking.sort_values('score_rubric', ascending=False).reset_index(drop=True)
ranking['rank'] = ranking.index + 1
ranking = ranking[['rank', 'modelo', 'tipo', 'provedor', 'score_rubric',
                  'avaliacao_final', 'nota_consenso',
                  'output_tokens_real', 'latencia_mediana',
                  'convergencia_gpt_opus', 'n_divergencias']].round(4)

print('Top 11 modelos pelo score do rubric unificado:')
print(ranking.to_string(index=False))

# ============================================================================
# BLOCO 6 — Cruzamento: Qualidade × Concisão (só API, onde temos avaliacao_final)
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 6 — Qualidade × Concisão (9 modelos API)')
print('═' * 70)

# Pegar avaliacao_final por modelo (API) e cruzar com score_rubric (concisão+correção)
api_qual = df_av.groupby('modelo')['avaliacao_final'].mean()
api_score = df_uni[df_uni['tipo'] == 'api'].groupby('modelo')['score'].mean()
api_tokens = df_op.groupby('modelo')['output_tokens'].mean()
api_lat = df_op.groupby('modelo')['latencia_s'].median()

cross = pd.DataFrame({
    'avaliacao_final': api_qual,
    'score_rubric': api_score,
    'output_tokens': api_tokens,
    'latencia_mediana': api_lat,
})

# Correlações
r_quality_focus, p_quality_focus = stats.pearsonr(cross['avaliacao_final'], cross['score_rubric'])
r_tokens_score, p_tokens_score = stats.pearsonr(cross['output_tokens'], cross['score_rubric'])
r_tokens_qual, p_tokens_qual = stats.pearsonr(cross['output_tokens'], cross['avaliacao_final'])

print(f'\nCorrelações (n={len(cross)} modelos API):')
print(f'  avaliacao_final × score_rubric:  r = {r_quality_focus:+.3f}  (p = {p_quality_focus:.3f})')
print(f'  tokens × score_rubric:            r = {r_tokens_score:+.3f}  (p = {p_tokens_score:.3f})')
print(f'  tokens × avaliacao_final:        r = {r_tokens_qual:+.3f}  (p = {p_tokens_qual:.3f})')

cross_export = cross.round(4).reset_index().sort_values('score_rubric', ascending=False)

# ============================================================================
# BLOCO 7 — Divergências consolidadas (API + chats, 92 + 29 = 121)
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 7 — Divergências consolidadas (121 casos com árbitro humano)')
print('═' * 70)

# API: tem avaliacao_humana e modelo_correto
div_api = df_av[~df_av['convergencia']].copy()
div_api_export = div_api[['edital', 'modelo', 'provedor', 'id', 'categoria',
                           'avaliacao_gpt', 'avaliacao_opus', 'avaliacao_humana',
                           'modelo_correto']].copy()
div_api_export['fonte'] = 'api'

# Chats: já tem avaliacao_humana e modelo_correto
div_chat_export = df_chat_div[['edital', 'modelo', 'provedor', 'id', 'categoria',
                               'avaliacao_gpt', 'avaliacao_opus', 'avaliacao_humana',
                               'modelo_correto']].copy()
div_chat_export['fonte'] = 'chat'

divs = pd.concat([div_api_export, div_chat_export], ignore_index=True)

# Resumo: em quem o humano confiou mais?
resumo_divs = divs.groupby(['fonte', 'modelo_correto']).size().unstack(fill_value=0)
resumo_divs['total'] = resumo_divs.sum(axis=1)
print(f'\nDistribuição de "modelo_correto" (em quem o humano confiou):')
print(resumo_divs.to_string())

# ============================================================================
# BLOCO 8 — API vs Chat: comparação direta provedor a provedor
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 8 — API vs Chat (mesmo provedor)')
print('═' * 70)

# Para cada provedor, pegar o melhor modelo API e comparar com o chat
api_vs_chat_rows = []
for prov in ['openai', 'anthropic']:
    # melhor API daquele provedor (pelo score_rubric)
    api_models = ranking[(ranking['tipo'] == 'api') & (ranking['provedor'] == prov)]
    chat_models = ranking[(ranking['tipo'] == 'chat') & (ranking['provedor'] == prov)]
    if len(api_models) == 0 or len(chat_models) == 0:
        continue
    melhor_api = api_models.iloc[0]
    chat = chat_models.iloc[0]
    api_vs_chat_rows.append({
        'provedor': prov,
        'melhor_modelo_api': melhor_api['modelo'],
        'score_rubric_api': melhor_api['score_rubric'],
        'tokens_api': melhor_api['output_tokens_real'],
        'latencia_api_s': melhor_api['latencia_mediana'],
        'chat': chat['modelo'],
        'score_rubric_chat': chat['score_rubric'],
        'tokens_chat': chat['output_tokens_real'],
        'delta_score': melhor_api['score_rubric'] - chat['score_rubric'],
        'delta_tokens': melhor_api['output_tokens_real'] - chat['output_tokens_real'],
    })
api_vs_chat = pd.DataFrame(api_vs_chat_rows).round(3)
print(api_vs_chat.to_string(index=False))

# ============================================================================
# BLOCO 9 — Detalhes por edital e categoria
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 9 — Por edital e categoria')
print('═' * 70)

heat_modelo_edital = df_uni.pivot_table(
    index='modelo', columns='edital', values='score', aggfunc='mean').round(3)
heat_modelo_edital['media'] = heat_modelo_edital.mean(axis=1).round(3)
heat_modelo_edital = heat_modelo_edital.sort_values('media', ascending=False)

heat_modelo_cat = df_uni.pivot_table(
    index='modelo', columns='categoria', values='score', aggfunc='mean').round(3)
heat_modelo_cat['media'] = heat_modelo_cat.mean(axis=1).round(3)
heat_modelo_cat = heat_modelo_cat.sort_values('media', ascending=False)

print('Score médio por modelo × edital:')
print(heat_modelo_edital.to_string())

# ============================================================================
# BLOCO 10 — Análise por provedor
# ============================================================================
print('\n' + '═' * 70)
print('BLOCO 10 — Por provedor (consolidação)')
print('═' * 70)

prov_stats = (
    df_uni.groupby('provider')
    .agg(score_medio=('score', 'mean'),
         taxa_perfeita=('score', lambda x: (x == 1.0).mean()),
         tokens_media=('n_tokens', 'mean'),
         n_total=('score', 'count'))
    .round(3).reset_index()
    .sort_values('score_medio', ascending=False)
    .rename(columns={'provider': 'provedor'}))
print(prov_stats.to_string(index=False))

# ============================================================================
# BLOCO 11 — Metadados do estudo
# ============================================================================
metadados = pd.DataFrame([
    ['data_consolidacao',          pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')],
    ['tokenizador',                TOKENIZER],
    ['n_modelos_total',            ranking['modelo'].nunique()],
    ['n_modelos_api',              df_av['modelo'].nunique()],
    ['n_modelos_chat',             df_uni[df_uni['tipo']=='chat']['modelo'].nunique()],
    ['n_editais',                  df_av['edital'].nunique()],
    ['n_categorias',               df_av['categoria'].nunique()],
    ['n_perguntas_por_edital',     df_av.groupby('edital')['id'].nunique().iloc[0]],
    ['n_linhas_qualidade_api',     len(df_av)],
    ['n_linhas_metricas_api',      len(df_me)],
    ['n_linhas_rubric_unificado',  len(df_uni)],
    ['n_divergencias_api',         int(n_div)],
    ['n_divergencias_chats',       len(df_chat_div)],
    ['kappa_gpt_opus_api',         round(kappa_api, 4)],
    ['convergencia_api',           round(conv_api, 4)],
    ['corr_qualidade_x_concisao',  f'{r_quality_focus:+.3f} (p={p_quality_focus:.3f})'],
    ['corr_tokens_x_score',        f'{r_tokens_score:+.3f} (p={p_tokens_score:.3f})'],
    ['fonte_qualidade_api',        'GPT + Opus + humano em divergências'],
    ['fonte_qualidade_chat',       'Rubric unificado (0/0.5/1) — correção + foco'],
    ['fonte_concisao',             'Rubric unificado + tokens calculados via tiktoken'],
], columns=['campo', 'valor'])

# ============================================================================
# EXPORTAR Excel mestre
# ============================================================================
print('\n' + '═' * 70)
print('Exportando Excel mestre')
print('═' * 70)

out_xlsx = OUT / 'tcc_analise_integrada.xlsx'

with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    ranking.to_excel(writer, sheet_name='01_ranking_unificado', index=False)
    rubric_por_modelo.to_excel(writer, sheet_name='02_rubric_unificado', index=False)
    df_av.groupby(['modelo', 'provedor']).agg(
        avaliacao_final=('avaliacao_final', 'mean'),
        nota_consenso=('nota_consenso', 'mean'),
        convergencia=('convergencia', 'mean'),
        n_divergencias=('convergencia', lambda x: (~x).sum()),
    ).round(4).reset_index().sort_values(
        'avaliacao_final', ascending=False).to_excel(
        writer, sheet_name='03_qualidade_api', index=False)
    op_por_modelo.to_excel(writer, sheet_name='04_metricas_operacionais', index=False)
    cross_export.to_excel(writer, sheet_name='05_qualidade_x_concisao', index=False)
    api_vs_chat.to_excel(writer, sheet_name='06_api_vs_chat', index=False)
    divs.to_excel(writer, sheet_name='07_divergencias_humanas', index=False)
    heat_modelo_edital.reset_index().to_excel(writer, sheet_name='08_modelo_x_edital', index=False)
    heat_modelo_cat.reset_index().to_excel(writer, sheet_name='09_modelo_x_categoria', index=False)
    prov_stats.to_excel(writer, sheet_name='10_por_provedor', index=False)
    metadados.to_excel(writer, sheet_name='11_metadados', index=False)

print(f'✓ {out_xlsx}')
print(f'  abas: 01 ranking | 02 rubric | 03 qualidade_api | 04 metricas')
print(f'        05 qualidade×concisao | 06 api_vs_chat | 07 divergências')
print(f'        08 modelo×edital | 09 modelo×categoria | 10 provedor | 11 metadados')

# Salvar dataframes intermediários para os notebooks
INTER = OUT / 'intermediarios'
INTER.mkdir(exist_ok=True)
df_av.to_pickle(INTER / 'df_av_com_humano.pkl')
df_op.to_pickle(INTER / 'df_op.pkl')
df_uni.to_pickle(INTER / 'df_uni_com_tokens.pkl')
ranking.to_pickle(INTER / 'ranking.pkl')
cross.reset_index().to_pickle(INTER / 'cross_qual_concisao.pkl')
divs.to_pickle(INTER / 'divergencias.pkl')

print(f'✓ dataframes intermediários em {INTER}/')
print('\nDONE.')
