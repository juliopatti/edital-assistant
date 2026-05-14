"""
Streamlit UI — Interface de chat com o agente.

Rodar com: streamlit run app.py
"""

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

from agent.agent import build_agent, ask
from config import settings
from database.db import listar_editais

import warnings
import os
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --- Page config ---
st.set_page_config(
    page_title="Assistente de Editais",
    page_icon="📋",
    layout="centered",
)

st.title("📋 Assistente de Editais")
st.caption("💡 Escolha seu provedor e modelo de preferência na **barra lateral** (⚙️ à esquerda).")


# --- Sidebar: config ---
with st.sidebar:
    st.header("⚙️ Configuração")

    provider_options = ["openai", "anthropic", "deepseek"]
    default_provider = "openai"
    provider_index = provider_options.index(default_provider)
    provider = st.selectbox(
        "Provider",
        options=provider_options,
        index=provider_index,
    )

    model_options = {
        "openai": [
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-4o-mini",
            "gpt-5.5",
        ],
        "deepseek": [
            "deepseek-v4-flash",
            "deepseek-v4-pro",
        ],
        "anthropic": [
            "claude-haiku-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        ],
    }

    model = st.selectbox(
        "Modelo",
        options=model_options.get(provider, []),
    )

    # Se provider ou modelo mudou, força recriar o agente.
    # Não limpa o histórico — pra testar o mesmo turno em modelos diferentes.
    chave_modelo_atual = (provider, model)
    if st.session_state.get("modelo_anterior") != chave_modelo_atual:
        st.session_state.pop("agent", None)
        st.session_state.modelo_anterior = chave_modelo_atual

    st.divider()
    st.markdown("**Edital ativo**")

    editais = listar_editais()

    if not editais:
        st.info("Nenhum edital ingerido ainda. Vá na página Admin para ingerir.")
        st.stop()

    opcoes = {f"{e.orgao} — {e.numero_edital}": e.id for e in editais}
    opcoes["Todos os editais"] = 0

    label_escolhido = st.selectbox(
        "Selecione o edital desta conversa",
        options=list(opcoes.keys()),
        key="edital_label",
    )
    edital_id_ativo = opcoes[label_escolhido]

    # Se o edital mudou, reseta conversa e agente
    if st.session_state.get("edital_id_anterior") != edital_id_ativo:
        st.session_state.messages = []
        st.session_state.pop("agent", None)
        st.session_state.edital_id_anterior = edital_id_ativo

    if st.button("🔄 Reiniciar conversa"):
        st.session_state.messages = []
        st.session_state.pop("agent", None)
        st.rerun()

    memoria_ativa = st.toggle(
        "🧠 Memória do chat",
        value=False,
        help=(
            "Ligado: o agente lê o histórico desta conversa antes de responder. "
            "Desligado: cada pergunta é tratada de forma independente, sem "
            "contexto das anteriores. (As mensagens continuam visíveis na tela.)"
        ),
    )
    if not memoria_ativa:
        st.caption("⚠️ Cada pergunta será respondida sem contexto das anteriores.")

    st.divider()
    st.markdown("**Status do sistema**")
    st.write(f"Editais cadastrados: {len(editais)}")
    for e in editais:
        st.write(f"· {e.orgao} — {e.numero_edital}")


# --- Agent init ---
def get_agent():
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = build_agent(provider=provider, model=model)
        except Exception as e:
            st.error(f"Erro ao inicializar o agente: {e}")
            st.stop()
    return st.session_state.agent


# --- Chat state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render histórico
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# Input do usuário
if prompt := st.chat_input("Pergunte sobre editais de concursos..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            agent = get_agent()
            historico_pra_agente = (
                st.session_state.messages[:-1] if memoria_ativa else []
            )
            try:
                response = ask(
                    agent=agent,
                    question=prompt,
                    chat_history=historico_pra_agente,
                    edital_id_ativo=edital_id_ativo,
                )
            except Exception as e:
                response = f"Erro ao processar: {str(e)}"

        st.markdown(response)

    st.session_state.messages.append(AIMessage(content=response))