# estudos_integrados_v3

Reanálise focada do estudo de modelos para consulta a editais (BNDES, CVM, Petrobras), reescrita a partir do feedback à v2 para um recorte mais direto e voltado à defesa do TCC.

## O que mudou em relação à v2

- **Quatro dimensões, na ordem de importância**. O estudo agora é organizado em torno de **precisão (principal), concisão (segunda), latência e custo**. Recortes secundários (categoria, edital, divergência de juízes) ainda existem, mas em segundo plano.
- **Provedor "Anthropic"**. O antigo `familia = "Claude"` virou `provedor = "Anthropic"`, em paridade nominal com OpenAI e DeepSeek.
- **Convenção visual fixa**:
  - **Cor = provedor**: OpenAI (verde `#10A37F`), Anthropic (laranja `#D97757`), DeepSeek (azul `#4D6BFE`).
  - **Forma = canal**: **bolinha (`o`) = API**, **quadrado (`s`) = Chat web**. Em barras, traduzido como sólido vs hachurado (`///`).
- **Comparações em pares e agrupadas**. Toda dimensão tem ranking geral + pareadas (Chat vs API do mesmo provedor) + small multiples por provedor.
- **Rótulos editáveis nos scatters**. A função `anota_sem_sobrepor` usa por default um dict `offsets_manuais={label: (dx, dy)}` que está explícito no código de cada scatter — você ajusta visualmente sem brigar com algoritmo. `adjustText` continua disponível via `usar_adjust=True`.
- **Concisão usa tokens-saída como métrica contínua**. A correlação Spearman entre tokens da resposta e `concisao_score` é **−0,989** ao nível de modelo, validando a substituição da medida binária por uma contínua mais legível em barras e scatters.
- **Score híbrido transparente em 3 variantes**. Fórmulas explícitas (Q de qualidade, P de produção, E de economia), ranking lado a lado e recomendação por perfil de uso fechando o estudo.

## Estrutura

```
estudos_integrados_v3/
├── README.md
├── data/
│   └── result_unificado_final.xlsx     ← fonte única
├── utils.py                            ← carregamento, paleta, helpers
├── 01_panorama.ipynb                   ← visão geral e tabela compacta
├── 02_precisao.ipynb                   ← dimensão principal
├── 03_concisao.ipynb                   ← segunda dimensão (tokens-saída)
├── 04_latencia.ipynb                   ← terceira (apenas API)
├── 05_custo.ipynb                      ← quarta (apenas API)
└── 06_sintese.ipynb                    ← 4 dimensões num plot + score híbrido + recomendação  ★
```

## Ordem de leitura

Quem tem 30 minutos: leia só o **06_sintese.ipynb**, que recapitula tudo.

Quem tem 2 horas: leia na ordem 01 → 02 → 03 → 04 → 05 → 06.

Cada notebook é autônomo (carrega o dado e configura o estilo do zero), então podem ser lidos em qualquer ordem isoladamente.

## Convenções de redação

- **Títulos acima dos gráficos**, em negrito; subtítulos logo abaixo em cinza, via helper `titulo_acima()`.
- **Rótulos editáveis** nos pontos de scatter, via `anota_sem_sobrepor(..., offsets_manuais={...})`. Para mover um rótulo específico, edite a entrada no dict.
- **Custo em escala log** sempre que aparecer (variação total de 75× entre Flash e Opus).
- **Latência e custo só para API.** Chat web aparece com célula vazia ou marcador cinza.
- **Sem Wilson, sem Cohen κ.** Quando aparece IC, é bootstrap simples. Concordância de juízes é uma porcentagem.

## Como rodar

```bash
pip install pandas numpy matplotlib scipy openpyxl nbformat jupyter adjustText
jupyter notebook
```

Abra qualquer um dos `.ipynb` e execute as células em ordem. Tempo total de execução completa dos 6 notebooks: ~45 segundos.

## Dependência opcional

- **`adjustText`** dá rótulos reposicionados automaticamente. O default deste estudo é *não* usar (preferência por edição manual via offsets), mas você pode ativar com `anota_sem_sobrepor(..., usar_adjust=True)`.
