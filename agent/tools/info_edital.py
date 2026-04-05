"""Consulta dados diretos do edital, sem precisar do LLM."""

import json
from langchain_core.tools import tool
from database.db import get_connection


@tool
def info_edital(campo: str, orgao: str = "") -> str:
    """Retorna um dado específico do edital de forma direta: salário, vagas,
    datas, banca, requisitos, etc. Use para perguntas objetivas como
    'qual o salário?', 'quantas vagas?', 'qual a banca?'.

    Args:
        campo: o que o usuário quer saber (ex: 'salario', 'vagas', 'banca', 'cronograma')
        orgao: filtro por órgão. Vazio pega o mais recente.
    """

    conn = get_connection()
    if orgao:
        row = conn.execute(
            "SELECT dados_json FROM editais WHERE LOWER(orgao) LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{orgao.lower()}%",)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT dados_json FROM editais ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()

    if not row:
        return "Nenhum edital cadastrado."

    dados = json.loads(row["dados_json"])
    campo_lower = campo.lower()

    if "salari" in campo_lower or "remuner" in campo_lower:
        return f"Salário inicial: {dados.get('salario_inicial', 'não informado')}"

    if "vaga" in campo_lower:
        linhas = []
        for e in dados.get("enfases", []):
            vi = e.get("vagas_imediatas", {})
            cr = e.get("cadastro_reserva", {})
            linhas.append(
                f"{e['enfase']}: {vi.get('total',0)} imediatas, {cr.get('total',0)} reserva"
            )
        return "Vagas por ênfase:\n" + "\n".join(linhas)

    if "banca" in campo_lower:
        return f"Banca: {dados.get('banca', 'não informada')}"

    if "cronograma" in campo_lower or "data" in campo_lower:
        linhas = [f"- {c['evento']}: {c['data']}" for c in dados.get("cronograma", [])]
        return "Cronograma:\n" + "\n".join(linhas)

    if "benefici" in campo_lower:
        return "Benefícios: " + "; ".join(dados.get("beneficios", ["não informados"]))

    if "jornada" in campo_lower or "hora" in campo_lower:
        return f"Jornada: {dados.get('jornada_trabalho', 'não informada')}"

    if "requisit" in campo_lower:
        linhas = []
        for e in dados.get("enfases", []):
            reg = e.get("registro_profissional") or "não exigido"
            linhas.append(f"{e['enfase']}: {e['requisito_basico']} (registro: {reg})")
        return "Requisitos por ênfase:\n" + "\n".join(linhas)

    # Fallback: retorna os campos principais
    return json.dumps({
        "orgao": dados.get("orgao"),
        "edital": dados.get("numero_edital"),
        "cargo": dados.get("cargo"),
        "salario": dados.get("salario_inicial"),
        "banca": dados.get("banca"),
    }, ensure_ascii=False, indent=2)