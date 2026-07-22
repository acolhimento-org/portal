"""Orquestrador do pipeline: coleta todas as fontes e gera data/services.json.

Uso:
    python run.py                 # todas as fontes
    python run.py --only na_bmlt  # uma fonte específica (mantém as demais do JSON atual)

Princípio defensivo: se uma fonte falhar, os dados anteriores dela são mantidos
(nunca apagamos serviços por falha de coleta) e a falha fica registrada.
Snapshots crus são gravados em raw/ (em produção, enviados ao R2).
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

from connectors import cnes, na_bmlt
from normalize import now_iso

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data"
RAW = BASE / "raw"


def load_municipalities() -> list[dict]:
    path = DATA / "municipalities.json"
    if not path.exists():
        sys.exit("data/municipalities.json não existe. Rode fetch_municipalities.py primeiro.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_raw(source: str, payload) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "-")
    (RAW / f"{source}-{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def collect_cnes(munis: list[dict]) -> list[dict]:
    muni_by_code = {m["ibge6"]: m["name"] for m in munis}
    raw = cnes.fetch_raw()
    save_raw("cnes", raw)
    return cnes.to_services(raw, muni_by_code)


def collect_na(_munis) -> list[dict]:
    raw = na_bmlt.fetch_raw()
    save_raw("na_bmlt", raw)
    return na_bmlt.to_services(raw)


COLLECTORS = {
    "cnes": collect_cnes,
    "na_bmlt": collect_na,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=COLLECTORS.keys(), help="coletar só uma fonte")
    args = parser.parse_args()

    munis = load_municipalities()
    out_path = DATA / "services.json"
    existing: list[dict] = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    sources = [args.only] if args.only else list(COLLECTORS.keys())
    runs = []
    merged = {s["id"]: s for s in existing}

    for source in sources:
        started = now_iso()
        try:
            services = COLLECTORS[source](munis)
            # substitui todos os registros da fonte pelos recém-coletados
            merged = {k: v for k, v in merged.items() if v["source"] != source}
            for s in services:
                merged[s["id"]] = s
            runs.append({"source": source, "started_at": started, "finished_at": now_iso(),
                         "record_count": len(services), "status": "ok", "notes": None})
            print(f"[ok] {source}: {len(services)} serviços")
        except Exception:
            err = traceback.format_exc(limit=3)
            runs.append({"source": source, "started_at": started, "finished_at": now_iso(),
                         "record_count": 0, "status": "error", "notes": err})
            print(f"[ERRO] {source}: dados anteriores mantidos.\n{err}", file=sys.stderr)

    result = sorted(merged.values(), key=lambda s: s["id"])
    DATA.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "ingest_runs.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")

    by_kind = {}
    for s in result:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    print(f"Total: {len(result)} serviços -> {out_path}")
    print("Por tipo:", json.dumps(by_kind, ensure_ascii=False))

    if any(r["status"] == "error" for r in runs):
        sys.exit(1)


if __name__ == "__main__":
    main()
