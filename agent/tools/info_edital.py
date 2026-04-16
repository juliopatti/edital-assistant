"""Consulta dados estruturados de um edital por ID."""

import json
from langchain_core.tools import tool
from database.db import get_connection


@tool
def consultar_edital(edital_id: int, campo: str) -> str:
    """Consulta dados específicos de um edital usando seu ID numérico.

    Args:
        edital_id: ID numérico do edital (obtido via listar_editais).
        campo: o que consultar. Valores aceitos: salario, vagas, cronograma, provas, beneficios, jornada, requisitos, conteudo, etapas, tudo.
    """

    conn = get_connection()
    row = conn.execute(
        "SELECT dados_json, orgao FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()

    if not row:
        return (
            f"Edital com ID={edital_id} não encontrado. "
            "Use listar_editais() para ver os IDs disponíveis."
        )

    dados = json.loads(row["dados_json"])
    orgao = row["orgao"]
    campo_lower = campo.lower()

    if "tudo" in campo_lower or "geral" in campo_lower:
        partes = [
            f"Órgão: {dados.get('orgao')}",
            f"Edital: {dados.get('numero_edital')}",
            f"Cargo: {dados.get('cargo')}",
            f"Salário: {dados.get('salario_inicial')}",
            f"Jornada: {dados.get('jornada_trabalho')}",
            f"Regime: {dados.get('regime_contratacao')}",
            f"Banca: {dados.get('banca')}",
            f"Validade: {dados.get('prazo_validade')}",
        ]
        return "\n".join(partes)

    if "salari" in campo_lower or "remuner" in campo_lower:
        return f"Salário inicial ({orgao}): {dados.get('salario_inicial', 'não informado')}"

    if "vaga" in campo_lower:
        linhas = []
        for e in dados.get("enfases", []):
            vi = e.get("vagas_imediatas", {})
            cr = e.get("cadastro_reserva", {})
            linhas.append(
                f"{e['enfase']}: {vi.get('total',0)} imediatas "
                f"(AC:{vi.get('ampla_concorrencia',0)} CN:{vi.get('candidato_negro',0)} PcD:{vi.get('pessoa_com_deficiencia',0)}) "
                f"+ {cr.get('total',0)} reserva"
            )
        return f"Vagas ({orgao}):\n" + "\n".join(linhas) if linhas else "Nenhuma ênfase cadastrada."

    if "cronograma" in campo_lower or "data" in campo_lower or "inscri" in campo_lower:
        linhas = [f"- {c['evento']}: {c['data']}" for c in dados.get("cronograma", [])]
        return f"Cronograma ({orgao}):\n" + "\n".join(linhas) if linhas else "Cronograma não disponível."

    if "prova" in campo_lower or "nota" in campo_lower:
        linhas = []
        for p in dados.get("provas", []):
            linha = f"- {p['disciplina']}: {p['num_questoes']} questões, {p['total_pontos']} pts"
            if p.get("nota_minima"):
                linha += f", mínimo {p['nota_minima']} pts"
            linha += f" ({p['carater']})"
            linhas.append(linha)
        return f"Provas ({orgao}):\n" + "\n".join(linhas) if linhas else "Informações de provas não disponíveis."

    if "benefici" in campo_lower:
        return f"Benefícios ({orgao}): " + "; ".join(dados.get("beneficios", ["não informados"]))

    if "jornada" in campo_lower or "hora" in campo_lower:
        return f"Jornada ({orgao}): {dados.get('jornada_trabalho', 'não informada')}"

    if "requisit" in campo_lower:
        linhas = []
        for e in dados.get("enfases", []):
            reg = e.get("registro_profissional") or "não exigido"
            linhas.append(f"{e['enfase']}: {e['requisito_basico']} (registro: {reg})")
        return f"Requisitos ({orgao}):\n" + "\n".join(linhas) if linhas else "Requisitos não disponíveis."

    if "conteudo" in campo_lower or "ementa" in campo_lower or "programat" in campo_lower:
        linhas = []
        for e in dados.get("enfases", []):
            linhas.append(f"Conteúdo programático — {e['enfase']}:")
            for t in e.get("conteudo_programatico", []):
                linhas.append(f"  - {t}")
        basico = dados.get("conteudo_basico", {})
        if basico:
            linhas.append("Conteúdo básico (comum):")
            for disc, topicos in basico.items():
                linhas.append(f"  {disc}: {', '.join(topicos[:5])}")
        return "\n".join(linhas) if linhas else "Conteúdo programático não disponível."

    if "etapa" in campo_lower:
        linhas = []
        for et in dados.get("etapas", []):
            linhas.append(f"- {et['numero']}ª Etapa: {et['nome']} ({et['tipo']})")
        return f"Etapas ({orgao}):\n" + "\n".join(linhas) if linhas else "Etapas não disponíveis."

    campos_disponiveis = "salario, vagas, cronograma, provas, beneficios, jornada, requisitos, conteudo, etapas, tudo"
    return f"Campo '{campo}' não reconhecido. Campos disponíveis: {campos_disponiveis}"