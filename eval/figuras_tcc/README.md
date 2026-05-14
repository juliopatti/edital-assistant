# Figuras do TCC — Geração reproduzível

Este pacote contém o notebook que reproduz **exatamente** as 9 figuras usadas no TCC *Uso de LLMs com Retrieval-Augmented Generation para democratização do acesso à informação em editais de concursos públicos de Ciência de Dados*.

## Estrutura

```
figuras_tcc/
├── README.md                       # este arquivo
├── gerar_figuras.ipynb             # notebook principal
├── utils.py                        # helpers (paleta, ordem, dados, plotagem)
└── data/
    └── result_unificado_final.xlsx # base consolidada (1.650 respostas × 23 colunas)
```

Ao executar o notebook, será criada também a pasta `figs/` contendo os PNGs gerados.

## Dependências

- Python ≥ 3.10
- `pandas`, `numpy`, `matplotlib`, `scipy`, `openpyxl`
- (Opcional, apenas para rodar o notebook em si) `jupyter` ou `notebook`

Instalação rápida:

```bash
pip install pandas numpy matplotlib scipy openpyxl jupyter
```

## Como executar

### Opção 1: pelo Jupyter (interativo)

```bash
cd figuras_tcc
jupyter notebook gerar_figuras.ipynb
```

Execute as células em ordem (Cell → Run All). Cada figura é exibida na própria saída da célula e simultaneamente salva em `figs/`.

### Opção 2: pela linha de comando (em batch)

```bash
cd figuras_tcc
jupyter nbconvert --to notebook --execute gerar_figuras.ipynb --output executado.ipynb
```

## Conteúdo das células

| # | Tipo | Conteúdo |
|---|------|----------|
| 1 | md   | Capa e visão geral |
| 2 | md   | Setup |
| 3 | code | Imports, estilo, carga de `df` e `mestre` |
| 4–5 | md+code | **Figura 1** — Arquitetura geral |
| 6–7 | md+code | **Figura 2** — Pipeline de ingestão |
| 8–9 | md+code | **Gráfico 1** — Acurácia factual média |
| 10–11 | md+code | **Gráfico 2** — Concisão média |
| 12–13 | md+code | **Gráfico 3** — Custo médio por pergunta (API) |
| 14–15 | md+code | **Gráfico 4** — Latência mediana (API) |
| 16–17 | md+code | **Gráfico 5** — Custo × acurácia |
| 18–19 | md+code | **Gráfico 6** — Latência × acurácia |
| 20–21 | md+code | **Gráfico 7** — Concisão × tokens (Spearman ρ ≈ −0,989) |
| 22–23 | md+code | Verificação final |

## Resultados esperados

Após a execução, `figs/` deve conter:

```
fig_arquitetura.png        ~165 KB
fig_pipeline.png            ~83 KB
fig_acuracia_factual.png   ~130 KB
fig_concisao.png           ~125 KB
fig_custo.png              ~108 KB
fig_latencia.png           ~109 KB
fig_custo_x_acuracia.png   ~105 KB
fig_latencia_x_acuracia.png ~109 KB
fig_concisao_x_tokens.png  ~110 KB
```

O valor do coeficiente ρ de Spearman impresso na última célula deve ser **−0,9886** (p ≈ 1 × 10⁻⁸).

## Notas

- A paleta é fixa (`utils.CORES_PROVEDOR`): OpenAI verde `#10A37F`, Anthropic terracota `#D97757`, DeepSeek azul `#4D6BFE`.
- A convenção de marcadores é fixa: API = círculo (`o`), chat web = quadrado (`s`).
- A ordem dos modelos nos gráficos comparativos segue `utils.ORDEM_MODELOS`.
- Os offsets de cada rótulo nos scatters estão declarados explicitamente no código de cada célula, para que sejam editáveis caso você queira reposicionar um modelo específico.
