"""Connector CNES/DATASUS: CAPS e demais unidades tipo 70 (RAPS).

Fonte: API de dados abertos do Ministério da Saúde (DEMAS), sem autenticação.
A API pagina de 20 em 20; o total de unidades tipo 70 é ~3 mil, então a coleta
completa faz ~160 requisições.

A API não expõe o subtipo do CNES, então classificamos CAPS AD pelo padrão do
nome fantasia (ex.: "CAPS AD II DE BREVES", "CAPS ALCOOL E DROGAS ...").
"""

import re
import sys
import time

import requests

sys.path.insert(0, __file__.rsplit("connectors", 1)[0])
from normalize import make_service, now_iso, title_case_pt, to_uf  # noqa: E402

API_URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
TIPO_CAPS = 70
PAGE_SIZE = 20

# "AD" isolado ou colado ao nivel (ADI, ADII, ADIII, ADIV), alem de mencoes a alcool/drogas
RE_AD = re.compile(r"\bAD(?:I{1,3}|IV)?\b|ALCOOL|ÁLCOOL|DROGAS", re.IGNORECASE)
RE_CAPS = re.compile(r"\bCAPS\b|PSICOSSOCIAL|\bCAPSI\b|\bCAPS1\b|\bCAPS2\b|\bCAPS3\b", re.IGNORECASE)

DESCRIPTIONS = {
    "caps_ad": (
        "CAPS AD (Álcool e outras Drogas) é o serviço público e gratuito do SUS, "
        "especializado no cuidado de pessoas com problemas relacionados ao uso de "
        "álcool e outras drogas. Atendimento de porta aberta: não precisa de "
        "encaminhamento, basta chegar."
    ),
    "caps": (
        "CAPS (Centro de Atenção Psicossocial) é o serviço público e gratuito do SUS "
        "para cuidado em saúde mental. Em cidades sem CAPS AD, também acolhe "
        "demandas de álcool e outras drogas. Não precisa de encaminhamento."
    ),
    "raps_outro": (
        "Serviço da Rede de Atenção Psicossocial (RAPS) do SUS, público e gratuito."
    ),
}


def classify(nome_fantasia: str) -> str:
    name = nome_fantasia or ""
    if RE_AD.search(name):
        return "caps_ad"
    if RE_CAPS.search(name):
        return "caps"
    return "raps_outro"


def fetch_raw(session: requests.Session | None = None, max_pages: int = 500) -> list[dict]:
    """Percorre a paginação da API até esgotar os registros de tipo 70.

    status=1 e essencial: sem ele a API devolve tambem unidades DESATIVADAS
    (verificado empiricamente: unidades com codigo_motivo_desabilitacao aparecem
    sob status=0 e somem sob status=1). Sem o filtro, publicavamos 188 servicos
    fechados, o pior erro possivel para quem gasta a janela de motivacao indo ate la.
    """
    session = session or requests.Session()
    records: list[dict] = []
    for page in range(max_pages):
        offset = page * PAGE_SIZE
        for attempt in range(3):
            try:
                resp = session.get(
                    API_URL,
                    params={"codigo_tipo_unidade": TIPO_CAPS, "status": 1,
                            "limit": PAGE_SIZE, "offset": offset},
                    timeout=60,
                )
                resp.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        batch = resp.json().get("estabelecimentos", [])
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
    return records


# descricao_turno_atendimento do CNES -> rotulo humano. So afirmamos o que o
# cadastro diz; nada de inventar "dias uteis" onde a fonte nao especifica.
HOURS_LABELS = {
    "ATENDIMENTO CONTINUO DE 24 HORAS/DIA (PLANTAO:INCLUI SABADOS, DOMINGOS E FERIADOS)":
        ("24 horas, todos os dias (inclusive fins de semana e feriados)", True),
    "ATENDIMENTOS NOS TURNOS DA MANHA E A TARDE": ("manhã e tarde", False),
    "ATENDIMENTO NOS TURNOS DA MANHA, TARDE E NOITE": ("manhã, tarde e noite", False),
    "ATENDIMENTO COM TURNOS INTERMITENTES": ("turnos intermitentes", False),
    "ATENDIMENTO SOMENTE PELA MANHA": ("somente pela manhã", False),
    "ATENDIMENTO SOMENTE A TARDE": ("somente à tarde", False),
    "ATENDIMENTO SOMENTE A NOITE": ("somente à noite", False),
}


def parse_hours(descricao: str | None) -> tuple[str | None, bool]:
    """Devolve (rotulo, open_24h). Descricao desconhecida vira rotulo generico."""
    if not descricao:
        return None, False
    desc = descricao.strip().upper()
    if desc in HOURS_LABELS:
        return HOURS_LABELS[desc]
    if "24 HORAS" in desc:
        return "24 horas", True
    return descricao.strip().capitalize(), False


def to_services(raw: list[dict], muni_by_code: dict[str, str], collected_at: str | None = None) -> list[dict]:
    """Converte registros crus da API para o schema único.

    muni_by_code: mapa código IBGE de 6 dígitos -> nome do município.
    """
    collected_at = collected_at or now_iso()
    services = []
    for rec in raw:
        uf = to_uf(rec.get("codigo_uf"))
        city = muni_by_code.get(str(rec.get("codigo_municipio")))
        if not uf or not city:
            continue  # sem localização confiável não entra no portal
        kind = classify(rec.get("nome_fantasia") or "")
        phones = []
        if rec.get("numero_telefone_estabelecimento"):
            phones.append(str(rec["numero_telefone_estabelecimento"]).strip())
        address = rec.get("endereco_estabelecimento") or ""
        if rec.get("numero_estabelecimento"):
            address = f"{address}, {rec['numero_estabelecimento']}".strip(", ")
        hours, open_24h = parse_hours(rec.get("descricao_turno_atendimento"))
        services.append(make_service(
            id=f"cnes-{rec['codigo_cnes']}",
            kind=kind,
            audience="dependente",
            name=title_case_pt(rec.get("nome_fantasia") or rec.get("nome_razao_social")),
            description=DESCRIPTIONS[kind],
            address=title_case_pt(address) or None,
            neighborhood=title_case_pt(rec.get("bairro_estabelecimento") or "") or None,
            city=city,
            state=uf,
            lat=rec.get("latitude_estabelecimento_decimo_grau"),
            lng=rec.get("longitude_estabelecimento_decimo_grau"),
            phones=phones,
            email=(rec.get("endereco_email_estabelecimento") or "").strip().lower() or None,
            hours=hours,
            open_24h=open_24h,
            registry_updated_at=rec.get("data_atualizacao"),
            source="cnes",
            source_url=f"https://cnes.datasus.gov.br/pages/estabelecimentos/consultas.jsp?search={rec['codigo_cnes']}",
            source_updated_at=collected_at,
        ))
    return services
