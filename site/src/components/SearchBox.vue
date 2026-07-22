<template>
  <div class="searchbox">
    <label class="sb-label" for="city-input">Digite sua cidade</label>
    <div class="sb-row">
      <div class="sb-field">
        <svg class="sb-mag" width="19" height="19" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
          <path d="m16 16 4.5 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
        <input
          id="city-input"
          ref="input"
          v-model="query"
          type="text"
          autocomplete="off"
          enterkeyhint="search"
          placeholder="Ex.: Santos, Belo Horizonte, Recife…"
          role="combobox"
          :aria-expanded="results.length > 0"
          aria-controls="city-results"
          aria-autocomplete="list"
          @focus="ensureLoaded"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="go(results[cursor])"
          @keydown.esc="query = ''"
        />
      </div>
      <a class="btn secondary sb-near" href="/buscar/">
        <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z" fill="none" stroke="currentColor" stroke-width="1.8" />
          <circle cx="12" cy="10" r="2.4" fill="currentColor" />
        </svg>
        <span>Perto de mim</span>
      </a>
    </div>

    <ul v-if="results.length" id="city-results" class="sb-results" role="listbox">
      <li
        v-for="(c, i) in results"
        :key="c.state + c.slug"
        role="option"
        :aria-selected="i === cursor"
        :class="{ active: i === cursor }"
        @mousedown.prevent="go(c)"
        @mousemove="cursor = i"
      >
        <strong>{{ c.city }}</strong><span class="uf">/{{ c.state }}</span>
        <span v-if="c.total > 0" class="count">{{ c.total }}</span>
        <span v-else class="count zero">orientação</span>
      </li>
    </ul>
    <p v-else-if="query.length >= 2 && loaded" class="sb-empty">
      Nenhuma cidade encontrada para “{{ query }}”. Confira a grafia ou
      <a href="/buscar/">busque por localização</a>.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const query = ref('');
const cursor = ref(0);
const loaded = ref(false);
const cities = ref([]);

// remove acentos para a busca casar 'sao paulo' com 'São Paulo'
const strip = (t) => t.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

async function ensureLoaded() {
  if (loaded.value) return;
  const resp = await fetch('/data/cities.json');
  cities.value = await resp.json();
  loaded.value = true;
}

const results = computed(() => {
  if (query.value.length < 2) return [];
  const q = strip(query.value);
  return cities.value
    .filter((c) => strip(c.city).includes(q))
    .sort((a, b) => {
      const aStarts = strip(a.city).startsWith(q) ? 0 : 1;
      const bStarts = strip(b.city).startsWith(q) ? 0 : 1;
      return aStarts - bStarts || b.total - a.total;
    })
    .slice(0, 8);
});

watch(results, () => { cursor.value = 0; });

function move(delta) {
  cursor.value = Math.max(0, Math.min(results.value.length - 1, cursor.value + delta));
}

function go(c) {
  if (!c) return;
  // Cidade sem servico mapeado vai para a pagina de orientacao, nao para um 404
  window.location.href = c.total > 0
    ? `/${c.state.toLowerCase()}/${c.slug}/`
    : '/nao-encontrei/';
}
</script>

<style scoped>
.searchbox { position: relative; max-width: 580px; }
.sb-label { display: block; font-weight: 600; margin-bottom: var(--s2); font-size: .95rem; }
.sb-row { display: flex; gap: var(--s2); }

.sb-field { position: relative; flex: 1; display: flex; align-items: center; }
.sb-mag { position: absolute; left: 14px; color: var(--ink-soft); pointer-events: none; }
input {
  width: 100%; padding: 15px 18px 15px 44px; font-size: 1rem; font-family: inherit;
  color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 100px; min-height: 54px;
  box-shadow: var(--shadow);
}
input:hover { border-color: var(--primary); }
input::placeholder { color: var(--ink-soft); opacity: .8; }

.sb-near { white-space: nowrap; padding-inline: var(--s3); }

.sb-results {
  position: absolute; z-index: 20; left: 0; right: 0; margin: var(--s2) 0 0; padding: 0;
  list-style: none; background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius-sm); box-shadow: var(--shadow); overflow: hidden;
}
.sb-results li {
  padding: 12px 14px; cursor: pointer; display: flex; gap: var(--s1);
  align-items: baseline; min-height: 46px;
}
.sb-results li.active { background: var(--primary-soft); }
.uf { color: var(--ink-soft); }
.count {
  margin-left: auto; font-size: .75rem; color: var(--ink-soft);
  background: var(--surface-2); border-radius: 100px; padding: 0 7px;
}
.count.zero { background: var(--accent-soft); color: var(--accent-ink); }
.sb-empty { font-size: .9rem; color: var(--ink-soft); margin-top: var(--s2); }

@media (max-width: 520px) {
  .sb-near span { display: none; }
}
</style>
