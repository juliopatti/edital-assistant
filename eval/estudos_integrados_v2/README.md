# estudos_integrados_v2

Reanálise integrada do estudo de modelos para consulta a editais (BNDES, CVM, Petrobras), reescrita a partir do feedback à v1.

## O que mudou em relação à v1

- **Fonte única.** Tudo lê `data/result_unificado_final.xlsx`. Não há mais leitura paralela de `result_chats_final` e `result_ferramenta_final`.
- **Vocabulário.** O termo "correção" foi banido; usamos **precisão** (ou acurácia) consistentemente. "GPT" foi padronizado para **ChatGPT**.
- **Estatística enxuta.** Saiu Wilson, saiu Cohen κ. Intervalo de confiança quando aparece é bootstrap simples. Concordância entre juízes é uma porcentagem.
- **Tokens explícitos.** Em todo notebook fica claro a diferença entre `resposta_tokens_tiktoken` (texto final que o usuário lê) e `output_tokens` (fluxo interno: raciocínio + tool-calls + resposta).
- **Sem Pareto opaco.** Trade-offs viraram scatter rotulado com quadrante interpretado em linguagem clara.
- **Score híbrido transparente.** Três variantes lado a lado, **com fórmula visível**, para o leitor escolher qual prefere.
- **Justificativas dos juízes entraram em cena.** A coluna `justificativa_*` (1650 textos) era ignorada na v1; agora alimenta a seção qualitativa de divergência.
- **Categorias entraram em cena.** Análise por categoria de pergunta (Prova, Cargo, Inscrições, Concurso, Procedimentos), que estava de fora.

## Estrutura

```
estudos_integrados_v2/
├── README.md                          ← este arquivo
├── data/
│   └── result_unificado_final.xlsx    ← fonte única
├── utils.py                           ← carregamento e padronização
├── 01_panorama.ipynb                  ← do que se trata o estudo
├── 02_precisao.ipynb                  ← quem acerta mais; onde os juízes discordam
├── 03_concisao.ipynb                  ← quem responde direto ao ponto
├── 04_eficiencia_ferramenta.ipynb     ← custo, latência, fluxo interno
└── 05_sintese.ipynb                   ← consolidação final  ★
```

## Ordem de leitura

Quem tem 30 minutos: lê só o **05_sintese.ipynb**, que recapitula tudo.

Quem tem 2 horas: lê na ordem 01 → 02 → 03 → 04 → 05.

Cada notebook é autônomo (carrega o dado e configura o estilo do zero), então podem ser lidos em qualquer ordem isoladamente.

## Convenções

- **Cores por família**: ChatGPT = verde (`#10A37F`), Claude = laranja (`#D97757`), DeepSeek = azul (`#4D6BFE`).
- **Títulos acima dos gráficos**, em negrito; subtítulos logo abaixo, em cinza.
- **Rótulos em cima dos pontos** nos scatters (não em legenda separada).
- **Custo em escala log** sempre (variação de 75× justifica).

## Como rodar

```bash
pip install pandas numpy matplotlib scipy openpyxl nbformat jupyter
jupyter notebook
```

Abra qualquer um dos `.ipynb` e execute as células em ordem. Tempo total de execução completa dos 5 notebooks: ~30 segundos.
