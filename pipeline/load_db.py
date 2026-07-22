"""Gera o banco a partir de data/services.json + data/municipalities.json.

Uso:
    python load_db.py                 # cria/atualiza data/acolhimento.sqlite (dev local)
    python load_db.py --d1-sql out.sql  # gera SQL para `wrangler d1 execute acolhimento --file=out.sql`
"""

import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def service_row(s: dict) -> tuple:
    return (
        s["id"], s["kind"], s["audience"], s["cost"], s["name"], s.get("description"),
        s.get("address"), s.get("neighborhood"), s["city"], s["city_slug"], s["state"],
        s.get("lat"), s.get("lng"), json.dumps(s.get("phones") or [], ensure_ascii=False),
        s.get("email"), json.dumps(s.get("schedule") or [], ensure_ascii=False),
        1 if s.get("online") else 0,
        s.get("hours"), 1 if s.get("open_24h") else 0,
        (None if s.get("open_meeting") is None else (1 if s["open_meeting"] else 0)),
        1 if s.get("wheelchair") else 0, 1 if s.get("holidays") else 0,
        1 if s.get("court_card") else 0, s.get("directions"),
        s.get("registry_updated_at"),
        s["source"], s.get("source_url"),
        s["source_updated_at"], 1 if s.get("active", True) else 0,
    )


INSERT_SERVICE = """INSERT OR REPLACE INTO services
 (id, kind, audience, cost, name, description, address, neighborhood, city, city_slug,
  state, lat, lng, phones, email, schedule, online,
  hours, open_24h, open_meeting, wheelchair, holidays, court_card, directions,
  registry_updated_at, source, source_url, source_updated_at, active)
 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""

INSERT_MUNI = "INSERT OR REPLACE INTO municipalities (ibge_code, name, slug, state) VALUES (?,?,?,?)"


def build_sqlite(services, munis, path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("DELETE FROM services")
    conn.executemany(INSERT_SERVICE, [service_row(s) for s in services])
    conn.executemany(INSERT_MUNI, [(m["ibge_code"], m["name"], m["slug"], m["state"]) for m in munis])
    conn.commit()
    conn.close()
    print(f"SQLite: {len(services)} serviços, {len(munis)} municípios -> {path}")


def sql_quote(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build_d1_sql(services, munis, path: Path) -> None:
    lines = [(BASE / "schema.sql").read_text(encoding="utf-8"), "DELETE FROM services;"]
    for s in services:
        values = ",".join(sql_quote(v) for v in service_row(s))
        lines.append(INSERT_SERVICE.replace("?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?", values) + ";")
    for m in munis:
        values = ",".join(sql_quote(v) for v in (m["ibge_code"], m["name"], m["slug"], m["state"]))
        lines.append(INSERT_MUNI.replace("?,?,?,?", values) + ";")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"SQL D1: {len(lines)} statements -> {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1-sql", type=Path, help="gerar arquivo SQL para o D1 em vez de SQLite")
    args = parser.parse_args()

    services = load_json("services.json")
    munis = load_json("municipalities.json")
    if args.d1_sql:
        build_d1_sql(services, munis, args.d1_sql)
    else:
        build_sqlite(services, munis, DATA / "acolhimento.sqlite")


if __name__ == "__main__":
    main()
