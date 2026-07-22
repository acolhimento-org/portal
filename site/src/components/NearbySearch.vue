<template>
  <div>
    <div class="controls">
      <button class="btn" :disabled="status === 'loading'" @click="locate">
        <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z" fill="none" stroke="currentColor" stroke-width="1.8" />
          <circle cx="12" cy="10" r="2.4" fill="currentColor" />
        </svg>
        {{ status === 'loading' ? 'Localizando…' : 'Usar minha localização' }}
      </button>
      <label class="filter">
        <span>Mostrar</span>
        <select v-model="filter">
          <option value="all">Tudo (gratuito)</option>
          <option value="sus">Serviços do SUS (CAPS)</option>
          <option value="apoio">Grupos de apoio (NA)</option>
        </select>
      </label>
    </div>

    <p v-if="status === 'error'" class="warn" role="alert">
      Não foi possível obter sua localização. Verifique a permissão do navegador
      ou <a href="/">busque pela sua cidade</a>.
    </p>

    <div v-if="nearest.length" class="results">
      <div id="nearby-map" class="map" role="img" aria-label="Mapa com os serviços mais próximos"></div>
      <ol class="list">
        <li v-for="r in nearest" :key="r.id" :class="`tone-${toneOf(r.kind)}`">
          <span class="k">{{ kindShort[r.kind] || r.kind }}</span>
          <a :href="`/servico/${r.id}/`">{{ r.name }}</a>
          <span v-if="r.open24h" class="k k-24h">24h</span>
          <span class="meta">{{ r.city }}/{{ r.state }} · {{ r.dist.toFixed(1) }} km</span>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';

const status = ref('idle');
const filter = ref('all');
const points = ref([]); // [id, kind, nome, cidade, uf, city_slug, lat, lng]
const origin = ref(null);
let map = null;
let markers = [];
let leaflet = null;

const kindShort = {
  caps_ad: 'CAPS AD', caps: 'CAPS', raps_outro: 'SUS/RAPS',
  na: 'NA', aa: 'AA', alanon: 'Al-Anon',
};
const SUS = new Set(['caps_ad', 'caps', 'raps_outro']);
const toneOf = (kind) => (SUS.has(kind) ? 'sus' : kind === 'alanon' ? 'family' : 'support');

// A cor do marcador vem do CSS, então acompanha o tema claro/escuro
function toneColor(kind) {
  const css = getComputedStyle(document.documentElement);
  const token = SUS.has(kind) ? '--primary' : kind === 'alanon' ? '--family' : '--support';
  return css.getPropertyValue(token).trim() || '#1b6b52';
}

function haversine(lat1, lng1, lat2, lng2) {
  const rad = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lng2 - lng1) * rad) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}

async function locate() {
  status.value = 'loading';
  try {
    if (!points.value.length) {
      const resp = await fetch('/data/geo.json');
      points.value = await resp.json();
    }
    const pos = await new Promise((resolve, reject) =>
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 15000 }));
    origin.value = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    status.value = 'done';
  } catch {
    status.value = 'error';
  }
}

const nearest = computed(() => {
  if (!origin.value) return [];
  return points.value
    .filter(([, kind]) => {
      if (filter.value === 'sus') return SUS.has(kind);
      if (filter.value === 'apoio') return !SUS.has(kind);
      return true;
    })
    .map(([id, kind, name, city, state, citySlug, lat, lng, open24h]) => ({
      id, kind, name, city, state, citySlug, lat, lng,
      open24h: open24h === 1,
      dist: haversine(origin.value.lat, origin.value.lng, lat, lng),
    }))
    .sort((a, b) => a.dist - b.dist)
    .slice(0, 25);
});

watch(nearest, async (list) => {
  if (!list.length || !origin.value) return;
  await nextTick();
  if (!leaflet) {
    leaflet = await import('leaflet');
    await import('leaflet/dist/leaflet.css');
  }
  const L = leaflet.default ?? leaflet;
  if (!map) {
    map = L.map('nearby-map', { scrollWheelZoom: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap', maxZoom: 18,
    }).addTo(map);
  }
  markers.forEach((m) => m.remove());
  markers = [];
  const you = L.circleMarker([origin.value.lat, origin.value.lng], {
    radius: 8, color: '#1d4ed8', fillColor: '#3b82f6', fillOpacity: .9,
  }).addTo(map).bindPopup('Você está aqui');
  markers.push(you);
  const bounds = [[origin.value.lat, origin.value.lng]];
  for (const r of list) {
    const color = toneColor(r.kind);
    const m = L.circleMarker([r.lat, r.lng], {
      radius: 7, weight: 2, color, fillColor: color, fillOpacity: .85,
    }).addTo(map).bindPopup(
      `<strong>${r.name}</strong><br>${r.city}/${r.state}<br>` +
      `<a href="/servico/${r.id}/">ver detalhes</a>`,
    );
    markers.push(m);
    bounds.push([r.lat, r.lng]);
  }
  map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13 });
});
</script>

<style scoped>
.controls { display: flex; gap: var(--s4); align-items: center; flex-wrap: wrap; margin-bottom: var(--s4); }
.filter { display: flex; align-items: center; gap: var(--s2); font-size: .9rem; }
.filter span { color: var(--ink-soft); }
.filter select {
  padding: var(--s2); min-height: 44px; border-radius: 8px;
  border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  font-size: .92rem; font-family: inherit;
}
.warn {
  background: var(--alert-bg); border: 1px solid var(--alert-line); color: var(--alert-ink);
  border-radius: var(--radius); padding: var(--s3) var(--s4);
}
.map { height: 380px; border-radius: var(--radius); border: 1px solid var(--line); margin-bottom: var(--s4); }

.list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--s2); }
.list li {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--s2);
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius-sm); padding: var(--s3) var(--s4);
}
.list a { font-weight: 600; text-decoration: none; color: var(--ink); }
.list a:hover { text-decoration: underline; }
.meta { color: var(--ink-soft); font-size: .85rem; margin-left: auto; white-space: nowrap; }
.k {
  font-size: .72rem; font-weight: 700; border-radius: 100px; padding: 3px 10px;
  white-space: nowrap;
}
.k-24h { background: var(--accent-soft); color: var(--accent-ink); }
.tone-sus .k { background: var(--primary-soft); color: var(--primary-ink); }
.tone-support .k { background: var(--support-soft); color: var(--support); }
.tone-family .k { background: var(--family-soft); color: var(--family); }
</style>
