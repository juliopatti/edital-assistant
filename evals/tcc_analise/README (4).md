# TCC — Análise integrada (LLMs em editais públicos)

Estudo unificado da avaliação de 11 modelos (9 via API + 2 chats comerciais) em
três editais (BNDES, CVM, Petrobras), cruzando correção, concisão e métricas
operacionais.

## Estrutura

```
.
├── data/                                 # entradas (5 arquivos)
│   ├── df_avaliacoes.xlsx                # 1.350 linhas — qualidade API (GPT+Opus)
│   ├── df_metricas.xlsx                  # 2.700 linhas — métricas API (latência/tokens)
│   ├── divergentes_human_eval.xlsx       # 92 — árbitro humano API
│   ├── chats_div_avaliado.xlsx           # 29 — árbitro humano chats
│   └── analise_consolidada.xlsx          # 1.650 — rubric unificado (correção+foco)
│
├── notebooks/
│   ├── 01_qualidade_api.ipynb            # avaliacao_final dos 9 modelos API
│   ├── 02_qualidade_chats.ipynb          # 2 chats: 29 divergências + score
│   ├── 03_concisao_global.ipynb          # 11 modelos: rubric + tokens
│   └── 04_integracao_tcc.ipynb           # cruzamentos + tese central
│
├── output/
│   ├── tcc_analise_integrada.xlsx        # ★ Excel mestre (11 abas)
│   └── intermediarios/                   # .pkl dos dataframes (consumidos pelos notebooks)
│
└── build_analysis.py                     # pipeline batch (gera o Excel mestre)
```

## Como rodar

1. Confira que os 5 arquivos em `data/` estão presentes
2. Pipeline batch (rápido — gera o Excel mestre e os intermediários):
   ```
   python build_analysis.py
   ```
3. Notebooks (em ordem):
   ```
   jupyter notebook notebooks/01_qualidade_api.ipynb
   jupyter notebook notebooks/02_qualidade_chats.ipynb
   jupyter notebook notebooks/03_concisao_global.ipynb
   jupyter notebook notebooks/04_integracao_tcc.ipynb
   ```

   O notebook 04 depende dos `.pkl` em `output/intermediarios/` — rode
   `build_analysis.py` antes ou execute o notebook 01 (que regenera o `df_av`
   com `avaliacao_final`).

## Abas do Excel mestre (`tcc_analise_integrada.xlsx`)

| Aba | O que tem |
|---|---|
| 01_ranking_unificado | 11 modelos com score, tokens, latência, qualidade |
| 02_rubric_unificado | Detalhe do rubric com IC Wilson, taxa_perfeita |
| 03_qualidade_api | Apenas 9 API: `avaliacao_final` + convergência |
| 04_metricas_operacionais | Latência (mediana, p90), tokens (in/out/cache), invocações |
| 05_qualidade_x_concisao | Cruzamento `avaliacao_final` × `score_rubric` × tokens |
| 06_api_vs_chat | Mesmo provedor — API vs chat |
| 07_divergencias_humanas | 92 + 29 = 121 casos com árbitro humano |
| 08_modelo_x_edital | Heatmap por edital |
| 09_modelo_x_categoria | Heatmap por categoria de pergunta |
| 10_por_provedor | OpenAI / Anthropic / DeepSeek consolidado |
| 11_metadados | Tokenizador, contagens, fontes |

## Achado central

Os 9 modelos API têm `avaliacao_final` entre **0.91 e 0.99** — em correção pura
estão quase empatados. Mas o `score_rubric` (correção + foco) varia de **0.62 a
0.93**. A diferença é prevista quase totalmente pelos tokens médios da resposta
(Pearson r = −0.82, p = 0.007).

**A escolha de LLM para editais não é uma questão de correção, é uma questão de
concisão.**

## Observações sobre dados

- A coluna `modelo` dos chats aparece como `std_chatgpt`/`std_claude` em
  `chats_div_avaliado.xlsx` e como `chatgpt`/`claude_chat` em
  `analise_consolidada.xlsx`. O pipeline normaliza para a segunda forma.
- Sem o consolidado das 300 avaliações GPT+Opus dos chats, não é possível
  replicar para os chats o método multi-juiz com árbitro do notebook 1.
  O `score` do rubric unificado é a medida de qualidade primária para os chats.
- Tokens calculados via `tiktoken cl100k_base`; quando indisponível
  (sem internet no sandbox), cai para um proxy por palavras com fator 1/0.75.
  Para reprodução com tiktoken real, rode localmente.
