"""Retorna a data de hoje. Usada para comparações de vigência/prazo."""

from datetime import date
from langchain_core.tools import tool


@tool
def data_hoje() -> str:
    """Retorna a data de hoje no formato DD/MM/AAAA.

    Use SEMPRE que a pergunta envolver:
    - vigência ("está aberto?", "ainda vale?", "já encerrou?")
    - prazos ("quanto tempo falta?", "posso me inscrever?")
    - comparação com datas do edital (inscrições, provas, homologação)

    Retorna string curta com a data, que você deve comparar com as datas do edital.
    """
    return date.today().strftime("%d/%m/%Y")
