"""Connector NA Brasil: reuniões de Narcóticos Anônimos via API BMLT (pública).

O BMLT devolve uma reunião por registro; agregamos por (nome do grupo + local)
para que cada grupo vire um serviço com a grade de horários no campo schedule.
"""

import re
import sys

import requests

sys.path.insert(0, __file__.rsplit("connectors", 1)[0])
from normalize import WEEKDAYS_PT, make_service, now_iso, slugify, to_uf  # noqa: E402

ROOT = "https://bmlt.na.org.br/ativo/main_server"
SEARCH_URL = f"{ROOT}/client_interface/json/?switcher=GetSearchResults"

DESCRIPTION = (
    "Grupo de Narcóticos Anônimos (NA), irmandade gratuita de mútua ajuda para "
    "quem quer parar de usar drogas. Não é preciso inscrição nem indicação: "
    "basta chegar em uma reunião. Reuniões 'abertas' aceitam visitantes e familiares."
)

# venue_type BMLT: 1 = presencial, 2 = virtual, 3 = híbrida
VIRTUAL_TYPES = {"2", "3"}


def fetch_raw() -> list[dict]:
    resp = requests.get(SEARCH_URL, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _fmt_time(value: str) -> str:
    return (value or "")[:5]  # "20:00:00" -> "20:00"


# Codigos de formato do BMLT do NA Brasil (decodificados via GetFormats):
#   A   = reuniao Aberta (familiares e interessados podem participar)
#   F   = reuniao Fechada (somente para quem tem o problema)
#   APC = Acesso Parcial a Cadeirantes
#   FuF = Funciona em Feriados
#   CAR = Carimbo para Beneficiario da Justica (comprovante de presenca)
def _formats(m: dict) -> set[str]:
    return {f.strip() for f in (m.get("formats") or "").split(",") if f.strip()}


def _directions(m: dict) -> str | None:
    """Instrucoes de chegada, do mais util ao menos: ponto de referencia + notas."""
    partes = [
        (m.get("location_text") or "").strip(),
        (m.get("location_info") or "").strip(),
    ]
    texto = ". ".join(p.rstrip(".") for p in partes if p)
    return texto or None


def to_services(raw: list[dict], collected_at: str | None = None) -> list[dict]:
    collected_at = collected_at or now_iso()
    groups: dict[str, dict] = {}
    for m in raw:
        uf = to_uf(m.get("location_province"))
        # alguns cadastros trazem a UF embutida na cidade ("Santos/SP")
        city = re.sub(r"\s*/\s*[A-Za-z]{2}$", "", (m.get("location_municipality") or "").strip())
        if not uf or not city:
            continue
        name = (m.get("meeting_name") or "Grupo de NA").strip()
        street = (m.get("location_street") or "").strip()
        online = str(m.get("venue_type") or "1") in VIRTUAL_TYPES
        fmts = _formats(m)
        key = f"na-{slugify(city)}-{slugify(name)}-{slugify(street)[:30]}"

        entry = groups.setdefault(key, {
            "id": key,
            "name": name,
            "address": street or None,
            "neighborhood": (m.get("location_neighborhood") or "").strip() or None,
            "city": city,
            "state": uf,
            "lat": float(m["latitude"]) if m.get("latitude") else None,
            "lng": float(m["longitude"]) if m.get("longitude") else None,
            "online": online,
            "schedule": [],
            "virtual_link": (m.get("virtual_meeting_link") or "").strip() or None,
            "open_any": False,      # alguma reuniao aberta?
            "format_seen": False,   # algum A/F informado? (sem isso, open_meeting = None)
            "wheelchair": False,
            "holidays": False,
            "court_card": False,
            "directions": None,
        })
        weekday = int(m.get("weekday_tinyint") or 0)
        if weekday in WEEKDAYS_PT:
            slot = {"weekday": WEEKDAYS_PT[weekday], "time": _fmt_time(m.get("start_time"))}
            # marca por reuniao se e aberta, quando o formato informa
            if "A" in fmts:
                slot["open"] = True
            elif "F" in fmts:
                slot["open"] = False
            if slot not in entry["schedule"]:
                entry["schedule"].append(slot)
        entry["online"] = entry["online"] or online
        if "A" in fmts or "F" in fmts:
            entry["format_seen"] = True
            entry["open_any"] = entry["open_any"] or ("A" in fmts)
        entry["wheelchair"] = entry["wheelchair"] or ("APC" in fmts)
        entry["holidays"] = entry["holidays"] or ("FuF" in fmts)
        entry["court_card"] = entry["court_card"] or ("CAR" in fmts)
        entry["directions"] = entry["directions"] or _directions(m)

    weekday_order = {name: i for i, name in enumerate(WEEKDAYS_PT.values())}
    services = []
    for g in groups.values():
        g["schedule"].sort(key=lambda s: (weekday_order.get(s["weekday"], 9), s["time"]))
        description = DESCRIPTION
        if g["virtual_link"]:
            description += f"\n\nLink da reunião online: {g['virtual_link']}"
        services.append(make_service(
            id=g["id"],
            kind="na",
            audience="dependente",
            name=g["name"],
            description=description,
            address=g["address"],
            neighborhood=g["neighborhood"],
            city=g["city"],
            state=g["state"],
            lat=g["lat"],
            lng=g["lng"],
            schedule=g["schedule"],
            online=g["online"],
            open_meeting=(g["open_any"] if g["format_seen"] else None),
            wheelchair=g["wheelchair"],
            holidays=g["holidays"],
            court_card=g["court_card"],
            directions=g["directions"],
            source="na_bmlt",
            source_url="https://www.na.org.br/grupo",
            source_updated_at=collected_at,
        ))
    return services
