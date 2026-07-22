"""Schema único e utilitários de normalização compartilhados pelos connectors."""

import re
import unicodedata
from datetime import datetime, timezone

# Códigos IBGE de UF -> sigla
UF_BY_CODE = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
    42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

UF_SIGLAS = set(UF_BY_CODE.values())

# Nome de estado por extenso -> sigla (fontes como BMLT podem usar qualquer um)
UF_BY_NAME = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR",
    "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}

WEEKDAYS_PT = {
    1: "Domingo", 2: "Segunda", 3: "Terça", 4: "Quarta",
    5: "Quinta", 6: "Sexta", 7: "Sábado",
}


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def slugify(text: str) -> str:
    text = strip_accents(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def to_uf(value) -> str | None:
    """Aceita código IBGE, sigla ou nome por extenso e devolve a sigla UF."""
    if value is None:
        return None
    if isinstance(value, int):
        return UF_BY_CODE.get(value)
    text = str(value).strip()
    if text.isdigit():
        return UF_BY_CODE.get(int(text))
    if text.upper() in UF_SIGLAS:
        return text.upper()
    return UF_BY_NAME.get(strip_accents(text).lower())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def title_case_pt(text: str) -> str:
    """Converte NOMES EM CAIXA ALTA do CNES para Título, preservando siglas."""
    keep_upper = {"CAPS", "AD", "ADI", "ADII", "ADIII", "ADIV",
                  "I", "II", "III", "IV", "UBS", "SUS", "CT", "NA", "AA"}
    small = {"de", "da", "do", "das", "dos", "e", "em", "a", "o"}
    words = []
    for i, w in enumerate(str(text or "").split()):
        wu = w.upper()
        if wu in keep_upper:
            words.append(wu)
        elif w.lower() in small and i > 0:
            words.append(w.lower())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def make_service(**kwargs) -> dict:
    """Cria um registro no schema único, validando campos obrigatórios."""
    required = ("id", "kind", "audience", "name", "city", "state", "source")
    for field in required:
        if not kwargs.get(field):
            raise ValueError(f"Campo obrigatório ausente: {field} em {kwargs.get('id')}")
    if kwargs["state"] not in UF_SIGLAS:
        raise ValueError(f"UF inválida: {kwargs['state']} em {kwargs['id']}")
    return {
        "id": kwargs["id"],
        "kind": kwargs["kind"],
        "audience": kwargs["audience"],
        "cost": kwargs.get("cost", "gratuito"),
        "name": kwargs["name"],
        "description": kwargs.get("description"),
        "address": kwargs.get("address"),
        "neighborhood": kwargs.get("neighborhood"),
        "city": kwargs["city"],
        "city_slug": slugify(kwargs["city"]),
        "state": kwargs["state"],
        "lat": kwargs.get("lat"),
        "lng": kwargs.get("lng"),
        "phones": kwargs.get("phones") or [],
        "email": kwargs.get("email"),
        "schedule": kwargs.get("schedule") or [],
        "online": bool(kwargs.get("online", False)),
        # Enriquecimento (nem toda fonte preenche tudo; None = desconhecido)
        "hours": kwargs.get("hours"),                       # texto: "24 horas, todos os dias"
        "open_24h": bool(kwargs.get("open_24h", False)),
        "open_meeting": kwargs.get("open_meeting"),         # True/False/None (NA: aberta a familiares?)
        "wheelchair": bool(kwargs.get("wheelchair", False)),
        "holidays": bool(kwargs.get("holidays", False)),    # funciona em feriados
        "court_card": bool(kwargs.get("court_card", False)),  # carimbo p/ beneficiario da Justica
        "directions": kwargs.get("directions"),             # instrucoes de chegada
        "registry_updated_at": kwargs.get("registry_updated_at"),  # data de atualizacao no cadastro da fonte
        "source": kwargs["source"],
        "source_url": kwargs.get("source_url"),
        "source_updated_at": kwargs.get("source_updated_at") or now_iso(),
        "active": True,
    }
