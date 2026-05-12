# estudos_integrados_refatorado

Sequência coerente de estudos para o TCC usando apenas os artefatos finais em Excel:

- `result_unificado_final.xlsx`
- `result_ferramenta_final.xlsx`
- `result_chats_final.xlsx`

Os notebooks não gravam bases intermediárias. Os campos derivados são criados em memória.

## Ordem sugerida

1. `00_preparacao_e_dicionario.ipynb` — padroniza nomes e mostra a estrutura dos artefatos.
2. `01_caracterizacao_da_base.ipynb` — mostra a composição da base por origem, modelo, edital e categoria.
3. `02_concordancia_dos_avaliadores.ipynb` — avalia a consistência dos julgadores automáticos.
4. `03_acerto_geral_dos_modelos.ipynb` — compara acerto médio, acerto total, parciais e erros.
5. `04_acerto_por_contexto.ipynb` — verifica se o desempenho muda por edital e categoria.
6. `05_erros_e_divergencias.ipynb` — explora erros, acertos parciais, divergências e justificativas.
7. `06_resposta_direta_e_foco.ipynb` — analisa objetividade/foco das respostas.
8. `07_custo_tempo_e_esforco_operacional.ipynb` — usa apenas a base da ferramenta para custo, latência e chamadas.
9. `08_tradeoffs_qualidade_eficiencia.ipynb` — cruza qualidade com eficiência operacional.
10. `09_ferramenta_vs_chats_comerciais.ipynb` — compara ferramenta/API com chats comerciais.
11. `10_sintese_e_ranking_para_tcc.ipynb` — consolida rankings e recomendações por cenário.

## Convenções de texto

- `avaliacao_final` vira **acerto**.
- `concisao_score` vira **resposta direta**.
- `convergencia` vira **concordância entre avaliadores**.
- `latencia_s` vira **tempo de resposta**.
- `n_invocacoes` vira **chamadas da ferramenta**.
- `custo_estimado_usd` vira **custo estimado**.

## Como rodar

Coloque esta pasta como `estudos_integrados/` no projeto. Os notebooks procuram os artefatos automaticamente em:

- `../artefatos/`
- `../../artefatos/`
- `artefatos/`
- `../`
- `.`

Não é necessário salvar `.pkl`, `.csv` ou bases auxiliares.
