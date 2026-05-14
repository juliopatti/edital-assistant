# Assistente de Editais — Concursos em Ciência de Dados

Ferramenta que responde perguntas sobre editais de concursos públicos com foco em Ciência de Dados.

## Setup

1. Criar e ativar ambiente virtual:

    python3.11 -m venv venv  
    
    source venv/bin/activate

2. Instalar dependências:

    pip install -r requirements.txt

3. Configurar variáveis de ambiente:

    cp .env.example .env

Editar `.env` com as chaves de API dos provedores que for usar:

    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    DEEPSEEK_API_KEY=...

4. Rodar:

    streamlit run app.py --logger.level error 2>/dev/null

5. (Opcional) Configurar LangSmith para rastreamento do agente:
   Adicionar no .env as variáveis LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY e LANGCHAIN_PROJECT.
   Criar conta gratuita em https://smith.langchain.com

## Ingerindo editais

Via terminal:

    python -m ingestion.ingest caminho/do/edital.pdf

Ou via interface: acesse a página Admin no menu lateral do Streamlit e use o upload.

## Reindexando a base vetorial (ChromaDB)

Necessário na primeira vez ou após deletar a pasta storage/chromadb/:

    python -c "
    from ingestion.rag import indexar_edital
    from database.db import get_connection
    conn = get_connection()
    rows = conn.execute('SELECT id, orgao, texto_completo FROM editais').fetchall()
    conn.close()
    for row in rows:
        print(f'Indexando: {row[1]}')
        indexar_edital(row[0], row[1], row[2])
    print('Pronto.')
    "

O modelo BGE-M3 (~2GB) será baixado automaticamente na primeira execução.

## Stack

- LLM (chat): OpenAI, Anthropic e DeepSeek — selecionáveis pela interface
- Ingestão de PDF: pypdf (split em capítulos) + Anthropic multimodal (PDF → markdown filtrado para Ciência de Dados)
- Orquestração: LangChain
- Interface: Streamlit
- Banco de dados: SQLite
- Busca vetorial: ChromaDB + BGE-M3 (BAAI)
- Modelos de dados: Pydantic v2

## Autores

- Julio Patti Pereira
- Leonardo Fernandes de Castro
- João Vítor Dallegrave