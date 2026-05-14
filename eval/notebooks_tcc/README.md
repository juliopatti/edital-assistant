# Estudo de quatro dimensões — 6 notebooks reproduzíveis

Conjunto de notebooks que reproduz as análises do TCC *Uso de LLMs com Retrieval-Augmented Generation para democratização do acesso à informação em editais de concursos públicos de Ciência de Dados*, sobre **1 650 respostas** (11 sistemas × 150 perguntas) avaliadas em quatro dimensões: **acurácia factual, concisão, custo e latência**.

## Estrutura

```
notebooks_tcc/
├── README.md
├── 01_panorama.ipynb        # Visão geral: perguntas, sistemas, plano 2D
├── 02_acuracia.ipynb        # Ranking, ICs, pareadas, juízes, heatmap
├── 03_concisao.ipynb        # Tokens × concisão, pareadas, distribuições
├── 04_latencia.ipynb        # Ranking, distribuição, trade-offs (só API)
├── 05_custo.ipynb           # Custo log, decomposição, trade-offs (só API)
├── 06_sintese.ipynb         # 4 dimensões num plot, scores híbridos, ranking
├── utils.py                 # Paleta, ordem, helpers de plot, carga de dados
└── data/
    └── result_unificado_final.xlsx  # Base consolidada
```

## Como executar

```bash
pip install pandas numpy matplotlib scipy openpyxl jupyter
jupyter notebook
```

Cada notebook é autônomo (basta executar as células em ordem), mas a leitura linear de 01 → 06 conta uma história coerente.

Para executar em batch sem abrir o navegador:

```bash
for nb in 01_panorama 02_acuracia 03_concisao 04_latencia 05_custo 06_sintese; do
  jupyter nbconvert --to notebook --execute "${nb}.ipynb" --output "exec_${nb}.ipynb"
done
```

## O que muda em relação ao TCC final (DOCX)

Os 9 gráficos do DOCX são uma **seleção** dos gráficos destes notebooks. Aqui você encontra:

- **Mais detalhes** em cada dimensão: intervalos de confiança bootstrap, distribuições (boxplots), pareadas Chat×API, heatmap modelo × categoria.
- **Concordância entre juízes** modelo a modelo (notebook 02), incluindo as 121 divergências (7,3%) que foram para revisão humana.
- **Decomposição** do output em "resposta visível" vs "fluxo interno" (notebook 05) — útil para entender de onde vem o custo.
- **Score híbrido transparente** em três pesos: Q (qualidade), P (produção balanceada), E (economia).

## Convenções usadas em todos os plots

- **Cor = provedor**: OpenAI verde `#10A37F`, Anthropic terracota `#D97757`, DeepSeek azul `#4D6BFE`.
- **Marcador = canal**: bolinha `o` para API instrumentada com RAG; quadrado `s` para chat web (ChatGPT e Claude usados pelo navegador).
- **Hachura `///`** em barras = chat web.
- **Ordem dos modelos** segue `utils.ORDEM_MODELOS`: OpenAI por capacidade, depois Anthropic, depois DeepSeek, depois chats web.
- **Custo e latência** só aparecem para os 9 modelos via API (não há mensuração padronizada para chats web).

## Atualizações em relação à versão anterior dos notebooks

- A dimensão antes chamada de "precisão" é agora **acurácia factual**, consistente com o TCC final.
- A escala da nota é **0 / 0,5 / 1** (não binária): 1 = correta, 0,5 = parcialmente correta, 0 = incorreta. Distribuição final: 1 497 / 133 / 20 respostas.
- Convergência entre os dois juízes-LLM: **92,67%** (1 529 de 1 650 avaliações); 121 divergências revisadas por avaliadores humanos.
- Em 112 das 121 divergências (92,6%), o juiz Claude havia sido mais brando. Avaliadores humanos concordaram com ChatGPT em 86 casos (71,1%) e com Claude em 35 (28,9%).

## Dependências

- Python ≥ 3.10
- `pandas`, `numpy`, `matplotlib`, `scipy`, `openpyxl`
- Para abrir o notebook: `jupyter` ou `jupyterlab`

## Sumário dos resultados-chave

| Dimensão | Líder | Valor | Lanterna | Valor |
|---|---|---|---|---|
| Acurácia factual | GPT-5.5 | 0,997 | ChatGPT (chat web) | 0,877 |
| Concisão | ChatGPT (chat web) | 1,000 | Claude (chat web) | 0,087 |
| Custo (API) | GPT-4o mini | US$ 0,0014 | Claude Opus 4.7 | US$ 0,1070 |
| Latência mediana (API) | GPT-5.4 mini | 2,67 s | GPT-5.5 | 19,51 s |

ρ de Spearman entre tokens médios na resposta e concisão média: **−0,989** (p < 0,001).
