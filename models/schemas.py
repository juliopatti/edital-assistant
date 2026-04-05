"""
Modelos Pydantic que definem a estrutura de dados dos editais.

Esses modelos servem como contrato central:
1. Validam a extração feita pelo LLM
2. Definem a estrutura das tabelas no SQLite
3. São o contrato que as tools do agente consomem

Projetados como "denominador comum" de editais de concurso brasileiros.
Campos que não existirem em um edital ficam como None ou lista vazia.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class VagasPorCategoria(BaseModel):
    ampla_concorrencia: int = 0
    pessoa_com_deficiencia: int = 0
    candidato_negro: int = 0
    total: int = 0


class CargoInfo(BaseModel):
    enfase: str = Field(description="Nome da ênfase, ex: 'Ciência de Dados'")
    requisito_basico: str = Field(default="", description="Requisito de formação")
    registro_profissional: str | None = Field(default=None, description="Conselho profissional exigido, se houver")
    vagas_imediatas: VagasPorCategoria = Field(default_factory=VagasPorCategoria)
    cadastro_reserva: VagasPorCategoria = Field(default_factory=VagasPorCategoria)
    conteudo_programatico: list[str] = Field(default_factory=list, description="Tópicos do conteúdo específico")


class EtapaSelecao(BaseModel):
    numero: int
    nome: str
    tipo: str = Field(description="eliminatório, classificatório, ou ambos")
    descricao: str = ""


class ProvaInfo(BaseModel):
    disciplina: str
    num_questoes: int = 0
    pontos_por_questao: float = 0
    total_pontos: float = 0
    nota_minima: float | None = None
    carater: str = Field(default="eliminatório e classificatório")


class CronogramaEvento(BaseModel):
    evento: str
    data: str = Field(description="Data como string, formato varia entre editais")


class EditalInfo(BaseModel):
    """Modelo principal que representa um edital completo."""

    # Identificação
    orgao: str = Field(description="Órgão/instituição do concurso")
    numero_edital: str = Field(default="")
    data_publicacao: str = Field(default="")
    banca: str = Field(default="")

    # Cargo geral
    cargo: str = Field(default="", description="Nome do cargo, ex: 'Analista'")
    salario_inicial: str = Field(default="")
    jornada_trabalho: str = Field(default="")
    beneficios: list[str] = Field(default_factory=list)
    regime_contratacao: str = Field(default="", description="CLT, estatutário, etc.")

    # Ênfases/vagas
    enfases: list[CargoInfo] = Field(default_factory=list)

    # Seleção
    etapas: list[EtapaSelecao] = Field(default_factory=list)
    provas: list[ProvaInfo] = Field(default_factory=list)
    criterios_desempate: list[str] = Field(default_factory=list)

    # Conhecimentos básicos (comuns)
    conteudo_basico: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Ex: {'Língua Portuguesa': ['Compreensão de texto', ...], ...}"
    )

    # Cronograma
    cronograma: list[CronogramaEvento] = Field(default_factory=list)

    # Regras gerais
    prazo_validade: str = Field(default="")
    locais_prova: str = Field(default="")

    # Metadata de controle (preenchido pelo sistema, não pelo LLM)
    arquivo_origem: str = Field(default="")
    data_extracao: str = Field(default_factory=lambda: datetime.now().isoformat())


class EditalResumo(BaseModel):
    """Resumo leve de um edital, para listagens e consultas rápidas."""

    id: int | None = None
    orgao: str
    numero_edital: str
    cargo: str
    salario_inicial: str
    total_vagas_foco: int = Field(default=0, description="Vagas na área de interesse (ex: Ciência de Dados)")
    data_publicacao: str
    status: str = Field(default="desconhecido", description="aberto, encerrado, em andamento")
