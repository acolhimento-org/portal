// Gera índices derivados de /data/services.json antes do build:
//  - src/data/cities.json  -> autocomplete e páginas de cidade
//  - public/data/geo.json  -> índice compacto p/ busca por proximidade no cliente
import { readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const servicesPath = join(root, 'data', 'services.json');

// O CSS do Leaflet vira asset estático: importá-lo pelo bundler faz o Vite
// promovê-lo a <link> no head, baixando 7KB em toda página de cidade mesmo
// para quem nunca abre o mapa. Servido daqui, ele só carrega no clique.
const leafletCss = join(here, '..', 'node_modules', 'leaflet', 'dist', 'leaflet.css');
if (existsSync(leafletCss)) {
  const vendorDir = join(here, '..', 'public', 'vendor');
  mkdirSync(vendorDir, { recursive: true });
  copyFileSync(leafletCss, join(vendorDir, 'leaflet.css'));
}

const outCities = join(here, '..', 'public', 'data', 'cities.json');
const outGeo = join(here, '..', 'public', 'data', 'geo.json');
mkdirSync(dirname(outCities), { recursive: true });
mkdirSync(dirname(outGeo), { recursive: true });

if (!existsSync(servicesPath)) {
  console.warn('[build-indexes] data/services.json não existe, gerando índices vazios (rode o pipeline).');
  writeFileSync(outCities, '[]');
  writeFileSync(outGeo, '[]');
  process.exit(0);
}

const services = JSON.parse(readFileSync(servicesPath, 'utf-8'));

const cities = new Map();
for (const s of services) {
  const key = `${s.state}/${s.city_slug}`;
  if (!cities.has(key)) {
    cities.set(key, { state: s.state, city: s.city, slug: s.city_slug, total: 0, byKind: {} });
  }
  const c = cities.get(key);
  c.total += 1;
  c.byKind[s.kind] = (c.byKind[s.kind] || 0) + 1;
}

// Municipios SEM servico tambem entram no autocomplete (total: 0). Sem isso,
// quem digita a propria cidade e nao acha nada conclui que o site quebrou;
// com isso, cai numa pagina que orienta o proximo passo (UBS, cidade vizinha).
const muniPath = join(root, 'data', 'municipalities.json');
if (existsSync(muniPath)) {
  const munis = JSON.parse(readFileSync(muniPath, 'utf-8'));
  for (const m of munis) {
    const key = `${m.state}/${m.slug}`;
    if (!cities.has(key)) {
      cities.set(key, { state: m.state, city: m.name, slug: m.slug, total: 0, byKind: {} });
    }
  }
}

const citiesArr = [...cities.values()].sort((a, b) =>
  a.city.localeCompare(b.city, 'pt-BR') || a.state.localeCompare(b.state));
writeFileSync(outCities, JSON.stringify(citiesArr));

// Índice geográfico compacto: [id, kind, nome, cidade, uf, city_slug, lat, lng]
const geo = services
  .filter((s) => s.lat != null && s.lng != null)
  .map((s) => [s.id, s.kind, s.name, s.city, s.state, s.city_slug,
    Math.round(s.lat * 1e5) / 1e5, Math.round(s.lng * 1e5) / 1e5,
    s.open_24h ? 1 : 0]);
writeFileSync(outGeo, JSON.stringify(geo));

console.log(`[build-indexes] ${citiesArr.length} cidades, ${geo.length} pontos geo, ${services.length} serviços.`);
