# Acolhimento

Portal social, gratuito e sem fins lucrativos que reúne num só lugar os serviços
**gratuitos** de ajuda para dependência de álcool e outras drogas no Brasil:
CAPS AD e demais serviços do SUS (RAPS) + grupos de apoio (NA; em breve AA e Al-Anon).

**Por quê:** essa informação existe, mas está espalhada (DATASUS, sites das irmandades,
PDFs do governo), e quem pesquisa no Google encontra primeiro anúncios de
clínicas pagas. Este projeto agrega as fontes oficiais, atualiza automaticamente e apresenta
sem viés comercial. Não existe "findtreatment.gov" brasileiro; este projeto quer ser isso.

## Estrutura

```
pipeline/   Coleta e normalização (Python, sem framework)
  connectors/cnes.py      CAPS/RAPS via API de dados abertos do Min. da Saúde
  connectors/na_bmlt.py   reuniões do NA Brasil via API BMLT
  fetch_municipalities.py base IBGE de municípios
  run.py                  orquestra tudo -> data/services.json
  load_db.py              gera SQLite local ou SQL para o Cloudflare D1
data/       Dados versionados (services.json é a base canônica do site)
site/       Portal (Astro + ilhas Vue 3 + Leaflet), deploy na Cloudflare
.github/workflows/
  ingest.yml   cron semanal: pipeline -> commit de data/ -> dispara deploy
  deploy.yml   build Astro -> wrangler deploy (Cloudflare)
```

## Rodando localmente

```bash
# 1. Pipeline (Python 3.11+)
cd pipeline
pip install -r requirements.txt
python fetch_municipalities.py   # uma vez (base IBGE)
python run.py                    # coleta CNES + NA (~3 min)

# 2. Site (Node 20+)
cd ../site
npm install
npm run dev                      # http://localhost:4321
```

## Deploy (Cloudflare)

1. `cd site && npx wrangler login` (uma vez).
2. `npm run build && npx wrangler deploy`.
3. No GitHub, configure os secrets `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID`
   para o deploy automático a cada push e após cada atualização de dados.

## Fontes de dados

| Fonte | Uso | Acesso |
|---|---|---|
| [CNES/DATASUS](https://cnes.datasus.gov.br) | CAPS, CAPS AD, RAPS | API dados abertos (sem token) |
| [NA Brasil](https://www.na.org.br/grupo) | Reuniões de NA | API BMLT (JSON público) |
| [IBGE](https://servicodados.ibge.gov.br) | Municípios | API pública |
| aa.org.br, al-anon.org.br | Grupos AA / Al-Anon | planejado (scraping respeitoso) |

## Princípios

- **Sem fins lucrativos**: nada de anúncios, leads ou cadastro pago.
- **Só fontes públicas/oficiais**; toda página mostra fonte e data da coleta.
- **Privacidade**: sem cadastro; geolocalização processada só no navegador.
- **Anonimato respeitado**: divulgamos locais de reunião, nunca pessoas.
- **Defensivo**: falha de coleta nunca apaga dados, mantém a última versão boa.
