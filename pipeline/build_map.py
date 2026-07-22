"""Converte a malha oficial do IBGE em paths SVG para o mapa do hero.

A malha vem da API de malhas territoriais do IBGE (dado público):
  https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=intermediaria

O GeoJSON cru tem 245KB, peso demais para o hero. Aqui projetamos em Mercator,
simplificamos com Douglas-Peucker e arredondamos as coordenadas, o que derruba
o tamanho em mais de 90% sem diferença visível no tamanho em que o mapa aparece.

Só a geometria é gravada. A contagem de serviços por estado é calculada no build
do site, a partir de services.json, para o mapa nunca ficar defasado dos dados.

Uso:
    python build_map.py            # usa pipeline/raw/malha-br.json
"""

import json
import math
from pathlib import Path

from normalize import UF_BY_CODE

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "raw" / "malha-br.json"
SAIDA = BASE.parent / "site" / "src" / "data" / "brazil-uf.json"

LARGURA = 760.0
TOLERANCIA = 0.06   # em graus; controla o quanto a costa é simplificada
CASAS = 1           # casas decimais nas coordenadas do path


def mercator(lng: float, lat: float) -> tuple[float, float]:
    """Projeção Web Mercator, que evita o Brasil achatado do equiretangular."""
    x = math.radians(lng)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def dist_ponto_reta(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(pontos: list, tol: float) -> list:
    if len(pontos) < 3:
        return pontos
    dmax, idx = 0.0, 0
    for i in range(1, len(pontos) - 1):
        d = dist_ponto_reta(pontos[i], pontos[0], pontos[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax <= tol:
        return [pontos[0], pontos[-1]]
    return (douglas_peucker(pontos[: idx + 1], tol)[:-1]
            + douglas_peucker(pontos[idx:], tol))


def aneis(geometria: dict) -> list:
    """Extrai os anéis externos, seja Polygon ou MultiPolygon."""
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"][0]]
    return [poligono[0] for poligono in geometria["coordinates"]]


def area_ring(anel: list) -> float:
    """Área por fórmula do shoelace, para achar o anel principal do estado."""
    s = 0.0
    for i in range(len(anel) - 1):
        x1, y1 = anel[i]
        x2, y2 = anel[i + 1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def centroide(anel: list) -> tuple[float, float]:
    """Centroide do polígono (não a média dos vértices, que puxa para onde há
    mais pontos, tipicamente o litoral recortado)."""
    cx = cy = a = 0.0
    for i in range(len(anel) - 1):
        x1, y1 = anel[i]
        x2, y2 = anel[i + 1]
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    if a == 0:
        return anel[0]
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def main():
    if not ENTRADA.exists():
        raise SystemExit(f"Malha não encontrada em {ENTRADA}. Baixe a malha do IBGE primeiro.")
    geo = json.loads(ENTRADA.read_text(encoding="utf-8"))

    # 1. simplifica em graus e guarda os anéis por UF
    por_uf: dict[str, list] = {}
    pins_geo: dict[str, tuple[float, float]] = {}
    for feicao in geo["features"]:
        uf = UF_BY_CODE.get(int(feicao["properties"]["codarea"]))
        if not uf:
            continue
        simplificados = []
        for anel in aneis(feicao["geometry"]):
            pontos = [(float(x), float(y)) for x, y in anel]
            s = douglas_peucker(pontos, TOLERANCIA)
            if len(s) >= 4:                      # descarta ilhotas irrelevantes
                simplificados.append(s)
        if not simplificados:
            continue
        por_uf[uf] = simplificados
        principal = max(simplificados, key=area_ring)
        pins_geo[uf] = centroide(principal)

    # 2. projeta tudo e descobre a moldura
    proj_uf = {uf: [[mercator(x, y) for x, y in anel] for anel in aneis_uf]
               for uf, aneis_uf in por_uf.items()}
    todos = [p for aneis_uf in proj_uf.values() for anel in aneis_uf for p in anel]
    minx = min(p[0] for p in todos); maxx = max(p[0] for p in todos)
    miny = min(p[1] for p in todos); maxy = max(p[1] for p in todos)
    escala = LARGURA / (maxx - minx)
    altura = (maxy - miny) * escala

    def para_tela(p):
        x, y = p
        return (round((x - minx) * escala, CASAS), round((maxy - y) * escala, CASAS))

    # 3. monta os paths
    estados = []
    for uf in sorted(proj_uf):
        partes = []
        for anel in proj_uf[uf]:
            pts = [para_tela(p) for p in anel]
            partes.append("M" + "L".join(f"{x} {y}" for x, y in pts) + "Z")
        px, py = para_tela(mercator(*pins_geo[uf]))
        estados.append({"uf": uf, "d": "".join(partes), "cx": px, "cy": py})

    saida = {
        "viewBox": f"0 0 {round(LARGURA)} {round(altura)}",
        "fonte": "Malha territorial do IBGE (dado público)",
        "estados": estados,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    kb = SAIDA.stat().st_size / 1024
    print(f"{len(estados)} estados, viewBox {saida['viewBox']}, {kb:.0f} KB -> {SAIDA}")


if __name__ == "__main__":
    main()
