"""
RAG v2: chunks estruturais (markdown com metadados) + BGE-M3 + ChromaDB.

Diferente da v1 (chunking fixo de 1000 chars sobre o texto bruto do pdfplumber),
aqui os chunks vêm do md_pipeline.md_chunker — split por headers com breadcrumb
prependado e metadados ricos (h1..h4, numero_secao, tipo, páginas, etc.).

API:
    - indexar_chunks(edital_id, chunks):     substitui chunks antigos desse edital
    - buscar_chunks(query, n_results, ...):  retrieval com filtros opcionais
    - get_chroma_collection():               acesso direto à coleção (usado no admin)
"""

import chromadb
from sentence_transformers import SentenceTransformer

from config import settings


# Paths
CHROMA_DIR = str(settings.base_dir / "storage" / "chromadb")


# Modelo carrega uma vez
_model = None


def get_model():
    global _model
    if _model is None:
        print("Carregando BGE-M3 (primeira vez pode demorar)...")
        _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name="editais",
        metadata={"hnsw:space": "cosine"},
    )


def indexar_chunks(edital_id: int, chunks: list[dict]) -> None:
    """
    Indexa chunks já prontos no ChromaDB, substituindo quaisquer chunks
    anteriores do mesmo edital_id.

    `chunks` deve ser o retorno de md_pipeline.md_chunker.chunk_edital:
        [{"texto": str, "metadata": dict}, ...]
    """
    if not chunks:
        print("  Nenhum chunk a indexar.")
        return

    model = get_model()
    collection = get_chroma_collection()

    # Remove chunks antigos desse edital (reindex idempotente)
    try:
        existing = collection.get(where={"edital_id": edital_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"  Removidos {len(existing['ids'])} chunks antigos do edital {edital_id}.")
    except Exception as e:
        print(f"  Aviso ao limpar chunks antigos: {e}")

    ids = [
        f"edital_{edital_id}_cap_{c['metadata']['cap_num']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]
    textos = [c["texto"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    print(f"  Gerando embeddings de {len(textos)} chunks (pode demorar em CPU)...")
    embeddings = model.encode(textos, show_progress_bar=True, batch_size=16)

    collection.add(
        ids=ids,
        documents=textos,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    print(f"  {len(textos)} chunks indexados no ChromaDB.")


def buscar_chunks(
    query: str,
    n_results: int = 10,
    orgao: str | None = None,
    edital_id: int | None = None,
    tipo: str | None = None,
) -> list[dict]:
    """
    Busca chunks relevantes para a query. Filtros opcionais combinados com AND.

    Args:
        query:      texto livre da pergunta
        n_results:  top-k
        orgao:      filtrar por órgão (ex: "BNDES")
        edital_id:  filtrar por ID do edital
        tipo:       "preambulo" | "corpo" | "anexo" | "apendice"

    Retorna list[dict] com chaves: texto, metadata, distancia.
    """
    model = get_model()
    collection = get_chroma_collection()

    query_embedding = model.encode([query])[0].tolist()

    # Monta filtro where (Chroma exige $and explícito quando há múltiplos)
    filtros: list[dict] = []
    if edital_id is not None:
        filtros.append({"edital_id": edital_id})
    if orgao is not None:
        filtros.append({"orgao": orgao})
    if tipo is not None:
        filtros.append({"tipo": tipo})

    where: dict | None
    if len(filtros) == 0:
        where = None
    elif len(filtros) == 1:
        where = filtros[0]
    else:
        where = {"$and": filtros}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "texto":     results["documents"][0][i],
            "metadata":  results["metadatas"][0][i],
            "distancia": results["distances"][0][i] if results["distances"] else None,
        })
    return chunks
