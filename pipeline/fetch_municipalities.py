"""Baixa a lista de municípios do IBGE e salva em data/municipalities.json.

A base muda raramente; rode manualmente quando necessário.
CNES usa código IBGE de 6 dígitos (sem dígito verificador), então guardamos os dois.
"""

import json
from pathlib import Path

import requests

from normalize import slugify

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
OUT = Path(__file__).resolve().parent.parent / "data" / "municipalities.json"


def main():
    resp = requests.get(IBGE_URL, timeout=120)
    resp.raise_for_status()
    rows = resp.json()
    munis = [
        {
            "ibge_code": str(r["municipio-id"]),          # 7 dígitos
            "ibge6": str(r["municipio-id"])[:6],           # como o CNES referencia
            "name": r["municipio-nome"],
            "slug": slugify(r["municipio-nome"]),
            "state": r["UF-sigla"],
        }
        for r in rows
    ]
    munis.sort(key=lambda m: (m["state"], m["slug"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(munis, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(munis)} municípios salvos em {OUT}")


if __name__ == "__main__":
    main()
