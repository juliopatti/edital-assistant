# estudos_integrados

Análises transversais que cruzam as três avaliações individuais (`avaliacao_judge_llms_tool/`,
`avaliacao_judge_llms_chats_comerciais/`, `concisao/`, `human_divergence_eval/`) e produzem
os achados de defesa do TCC.

Os artefatos consolidados (`result_unificado_final.xlsx`, `result_ferramenta_final.xlsx`,
`result_chats_final.xlsx`) vivem em `../artefatos/` e são produzidos pelos notebooks de
`../notebooks/`. Os notebooks deste diretório **só leem** esses artefatos — não rodam
avaliação.

## Estrutura do dataset unificado

`result_unificado_final.xlsx` (1650 linhas):

| Coluna | ferramenta (1350) | chat_comercial (300) |
|---|---|---|
| edital, modelo, id, categoria, pergunta, resposta | ✔️ | ✔️ |
| resposta_tokens_tiktoken | ✔️ | ✔️ |
| avaliacao_gpt + justificativa_gpt | ✔️ | ✔️ |
| avaliacao_opus + justificativa_opus | ✔️ | ✔️ |
| convergencia | ✔️ | ✔️ |
| avaliacao_humana + modelo_correto | só nas divergências (92) | só nas divergências (29) |
| **avaliacao_final** ∈ {0, 0.5, 1} | ✔️ | ✔️ |
| **concisao_score** ∈ {0, 1} + justificativa | ✔️ | ✔️ |
| input_tokens, output_tokens | ✔️ | `nao pertinente` |
| **custo_estimado_usd** | ✔️ | `nao pertinente` |
| n_invocacoes (loop agentic) | ✔️ | `nao pertinente` |
| latencia_s | ✔️ | `nao pertinente` |

## Notebooks

| # | Notebook | Dimensão | Origem usada |
|---|---|---|---|
| 01 | `qualidade_correcao.ipynb` | Correção (avaliacao_final, κ de Cohen, divergências) | unificado (1650) |
| 02 | `concisao_e_foco.ipynb` | Concisão (concisao_score, mineração de justificativas, trade-off com correção) | unificado (1650) |
| 03 | `custo_latencia_eficiencia.ipynb` | Economia (custo USD, latência p50/p95, n_invocacoes, Pareto) | ferramenta (1350) |
| 04 | `sintese_integrada_tcc.ipynb` | Cruzamento: quadrante 2×2, Pareto 3D, head-to-head ferramenta vs chats, score composto, resumo executivo | unificado (1650) |

## Como rodar

Cada notebook detecta automaticamente onde estão os artefatos procurando em `../artefatos/`,
`../../artefatos/`, `artefatos/`, `../` e `.`. Não há mais dependência de `.pkl` intermediários.

```python
# Setup mínimo no topo de cada notebook
ART = detecta_artefatos()
df = pd.read_excel(ART / 'result_unificado_final.xlsx')
```

## Convenções

- **Paleta por provedor**: anthropic `#D97757`, openai `#10A37F`, deepseek `#4D6BFE`
- **Origem**: ferramenta = círculo / borda preta; chat_comercial = quadrado / borda vermelha
- **Notas {0, 0.5, 1}**: 0 = errado, 0.5 = parcial, 1 = correto
- Modelos `std_*` são os **chats comerciais** (sem custo/latência); demais são da ferramenta API
