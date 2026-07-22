// Acesso central aos dados no build (páginas estáticas).
import servicesJson from '../../../data/services.json';

export interface Service {
  id: string;
  kind: string;
  audience: string;
  cost: string;
  name: string;
  description: string | null;
  address: string | null;
  neighborhood: string | null;
  city: string;
  city_slug: string;
  state: string;
  lat: number | null;
  lng: number | null;
  phones: string[];
  email: string | null;
  schedule: { weekday: string; time: string; open?: boolean }[];
  online: boolean;
  hours: string | null;
  open_24h: boolean;
  open_meeting: boolean | null;
  wheelchair: boolean;
  holidays: boolean;
  court_card: boolean;
  directions: string | null;
  registry_updated_at: string | null;
  source: string;
  source_url: string | null;
  source_updated_at: string;
  active: boolean;
}

export interface CityIndex {
  state: string;
  city: string;
  slug: string;
  total: number;
  byKind: Record<string, number>;
}

export const services = servicesJson as Service[];

const cityMap = new Map<string, CityIndex>();
for (const s of services) {
  const key = `${s.state}/${s.city_slug}`;
  if (!cityMap.has(key)) {
    cityMap.set(key, { state: s.state, city: s.city, slug: s.city_slug, total: 0, byKind: {} });
  }
  const c = cityMap.get(key)!;
  c.total += 1;
  c.byKind[s.kind] = (c.byKind[s.kind] || 0) + 1;
}
export const cities: CityIndex[] = [...cityMap.values()].sort(
  (a, b) => a.city.localeCompare(b.city, 'pt-BR') || a.state.localeCompare(b.state),
);

// Metadados de cada tipo de serviço (slug de URL, rótulos, contexto)
export const KINDS: Record<string, {
  slug: string; label: string; short: string; badge: string; freeLabel: string;
}> = {
  caps_ad: {
    slug: 'caps-ad',
    label: 'CAPS AD, para álcool e outras drogas (SUS)',
    short: 'CAPS AD',
    badge: 'SUS · Gratuito',
    freeLabel: 'Serviço público gratuito, sem encaminhamento',
  },
  caps: {
    slug: 'caps',
    label: 'CAPS, Centro de Atenção Psicossocial (SUS)',
    short: 'CAPS',
    badge: 'SUS · Gratuito',
    freeLabel: 'Serviço público gratuito, sem encaminhamento',
  },
  raps_outro: {
    slug: 'raps',
    label: 'Outros serviços de saúde mental do SUS (RAPS)',
    short: 'Serviço RAPS',
    badge: 'SUS · Gratuito',
    freeLabel: 'Serviço público gratuito',
  },
  na: {
    slug: 'na',
    label: 'Narcóticos Anônimos (NA)',
    short: 'Grupo de NA',
    badge: 'Grupo de apoio · Gratuito',
    freeLabel: 'Grupo de mútua ajuda, gratuito, basta chegar',
  },
  aa: {
    slug: 'aa',
    label: 'Alcoólicos Anônimos (AA)',
    short: 'Grupo de AA',
    badge: 'Grupo de apoio · Gratuito',
    freeLabel: 'Grupo de mútua ajuda, gratuito, basta chegar',
  },
  alanon: {
    slug: 'al-anon',
    label: 'Al-Anon, apoio para familiares e amigos',
    short: 'Grupo Al-Anon',
    badge: 'Para a família · Gratuito',
    freeLabel: 'Grupo de apoio para familiares, gratuito',
  },
};

export const kindBySlug = Object.fromEntries(
  Object.entries(KINDS).map(([kind, meta]) => [meta.slug, kind]),
);

export const SOURCE_LABELS: Record<string, { name: string; url: string }> = {
  cnes: {
    name: 'CNES, Cadastro Nacional de Estabelecimentos de Saúde (Ministério da Saúde)',
    url: 'https://cnes.datasus.gov.br',
  },
  na_bmlt: {
    name: 'Diretório oficial de reuniões do NA Brasil',
    url: 'https://www.na.org.br/grupo',
  },
};

export function servicesInCity(state: string, citySlug: string): Service[] {
  return services.filter((s) => s.state === state && s.city_slug === citySlug && s.active);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
}
