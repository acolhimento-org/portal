-- Schema do banco (D1/SQLite), Acolhimento
-- Tabela central: todos os serviços de ajuda, de qualquer fonte, num schema único.

CREATE TABLE IF NOT EXISTS services (
  id TEXT PRIMARY KEY,              -- slug estável: "cnes-2077485", "na-<hash>"
  kind TEXT NOT NULL,               -- 'caps_ad' | 'caps' | 'raps_outro' | 'na' | 'aa' | 'alanon'
  audience TEXT NOT NULL,           -- 'dependente' | 'familia' | 'ambos'
  cost TEXT NOT NULL DEFAULT 'gratuito',
  name TEXT NOT NULL,
  description TEXT,
  address TEXT,
  neighborhood TEXT,
  city TEXT NOT NULL,
  city_slug TEXT NOT NULL,
  state TEXT NOT NULL,              -- sigla UF
  lat REAL,
  lng REAL,
  phones TEXT,                      -- JSON array de strings
  email TEXT,
  schedule TEXT,                    -- JSON array [{weekday, time, open?}] quando houver
  online INTEGER NOT NULL DEFAULT 0,
  hours TEXT,                       -- rotulo humano do horario (CNES turno)
  open_24h INTEGER NOT NULL DEFAULT 0,
  open_meeting INTEGER,             -- NA: 1 aberta a familiares, 0 fechada, NULL desconhecido
  wheelchair INTEGER NOT NULL DEFAULT 0,
  holidays INTEGER NOT NULL DEFAULT 0,
  court_card INTEGER NOT NULL DEFAULT 0,
  directions TEXT,                  -- instrucoes de chegada
  registry_updated_at TEXT,         -- data de atualizacao no cadastro da fonte
  source TEXT NOT NULL,             -- 'cnes' | 'na_bmlt' | 'aa_scrape' | ...
  source_url TEXT,
  source_updated_at TEXT NOT NULL,  -- ISO da coleta (transparência na página)
  active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_services_geo ON services(lat, lng);
CREATE INDEX IF NOT EXISTS idx_services_city ON services(state, city_slug, kind);

-- Municípios (base IBGE), para autocomplete e páginas por cidade
CREATE TABLE IF NOT EXISTS municipalities (
  ibge_code TEXT PRIMARY KEY,       -- 7 dígitos IBGE
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  state TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_muni_slug ON municipalities(state, slug);

-- Log de execuções do pipeline (auditoria)
CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  record_count INTEGER,
  status TEXT NOT NULL,             -- 'ok' | 'error'
  notes TEXT
);
