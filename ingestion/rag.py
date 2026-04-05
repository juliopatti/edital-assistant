"""RAG v1: chunking fixo + BGE-M3 + ChromaDB."""

import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
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


def chunk_texto(texto: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Divide texto em chunks com overlap."""
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = inicio + chunk_size
        chunk = texto[inicio:fim]
        if chunk.strip():
            chunks.append(chunk.strip())
        inicio += chunk_size - overlap
    return chunks


def indexar_edital(edital_id: int, orgao: str, texto: str):
    """Chunka o texto, gera embeddings e salva no ChromaDB."""
    model = get_model()
    collection = get_chroma_collection()

    # Remove chunks antigos desse edital
    try:
        existing = collection.get(where={"edital_id": edital_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    chunks = chunk_texto(texto)
    print(f"  {len(chunks)} chunks gerados.")

    ids = [f"edital_{edital_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"edital_id": edital_id, "orgao": orgao, "chunk_index": i} for i in range(len(chunks))]

    print("  Gerando embeddings (pode demorar em CPU)...")
    embeddings = model.encode(chunks, show_progress_bar=True, batch_size=16)

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    print(f"  {len(chunks)} chunks indexados no ChromaDB.")


def buscar_chunks(query: str, n_results: int = 10, orgao: str = None) -> list[dict]:
    """Busca chunks relevantes pra uma query."""
    model = get_model()
    collection = get_chroma_collection()

    query_embedding = model.encode([query])[0].tolist()

    where = {"orgao": orgao} if orgao else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "texto": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distancia": results["distances"][0][i] if results["distances"] else None,
        })

    return chunks