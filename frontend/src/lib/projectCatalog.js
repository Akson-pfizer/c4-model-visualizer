/**
 * Architect Catalog client — metadata + cached C4 payloads live in the
 * backend SQLite database (see /api/catalog). Profile display name is also
 * stored server-side; a small localStorage mirror keeps the header snappy.
 */

const PROFILE_KEY = 'c4.profile.meta.v1';
/** Last opened / analyzed catalog project — restores Visualizer after reload. */
const ACTIVE_STUDIO_KEY = 'c4.studio.active.v1';

/**
 * @typedef {object} ActiveStudioState
 * @property {string} entryId
 * @property {string} [source]
 * @property {'local' | 'github'} [sourceType]
 * @property {string} [repoName]
 * @property {string} [savedAt]
 */

/**
 * @param {ActiveStudioState} state
 */
export function rememberActiveStudio(state) {
  if (!state?.entryId) return;
  try {
    localStorage.setItem(
      ACTIVE_STUDIO_KEY,
      JSON.stringify({
        entryId: state.entryId,
        source: state.source || '',
        sourceType: state.sourceType === 'github' ? 'github' : 'local',
        repoName: state.repoName || '',
        savedAt: nowIso()
      })
    );
  } catch {
    /* ignore quota */
  }
}

/** @returns {ActiveStudioState | null} */
export function getActiveStudio() {
  try {
    const raw = localStorage.getItem(ACTIVE_STUDIO_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.entryId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearActiveStudio() {
  try {
    localStorage.removeItem(ACTIVE_STUDIO_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * @typedef {object} CatalogEntry
 * @property {string} id
 * @property {string} source
 * @property {'local' | 'github'} source_type
 * @property {string} repo_name
 * @property {string} display_name
 * @property {string | null} [style]
 * @property {number} [node_count]
 * @property {number} [edge_count]
 * @property {number} view_count
 * @property {string} first_analyzed_at
 * @property {string} last_analyzed_at
 * @property {string} last_opened_at
 */

/**
 * @typedef {object} ProfileMeta
 * @property {string} display_name
 */

function nowIso() {
  return new Date().toISOString();
}

/**
 * @returns {ProfileMeta}
 */
export function getProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.display_name) return { display_name: parsed.display_name };
    }
  } catch {
    /* ignore */
  }
  return { display_name: 'Architect' };
}

/**
 * @param {Partial<ProfileMeta>} patch
 * @returns {Promise<ProfileMeta>}
 */
export async function updateProfile(patch) {
  const nextName = (patch.display_name || 'Architect').trim() || 'Architect';
  try {
    const res = await fetch('/api/catalog/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: nextName })
    });
    const data = await res.json().catch(() => ({}));
    const display_name = data.display_name || nextName;
    localStorage.setItem(
      PROFILE_KEY,
      JSON.stringify({ display_name, updated_at: nowIso() })
    );
    return { display_name };
  } catch {
    localStorage.setItem(
      PROFILE_KEY,
      JSON.stringify({ display_name: nextName, updated_at: nowIso() })
    );
    return { display_name: nextName };
  }
}

/**
 * @returns {Promise<ProfileMeta>}
 */
export async function fetchProfile() {
  try {
    const res = await fetch('/api/catalog/profile');
    const data = await res.json().catch(() => ({}));
    const display_name = data.display_name || 'Architect';
    localStorage.setItem(
      PROFILE_KEY,
      JSON.stringify({ display_name, updated_at: nowIso() })
    );
    return { display_name };
  } catch {
    return getProfile();
  }
}

/**
 * @param {string} [query]
 * @returns {Promise<CatalogEntry[]>}
 */
export async function listCatalog(query = '') {
  const params = new URLSearchParams();
  if (query.trim()) params.set('q', query.trim());
  const url = params.size ? `/api/catalog?${params}` : '/api/catalog';
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Catalog unavailable (${res.status})`);
  }
  const data = await res.json();
  if (data?.profile?.display_name) {
    localStorage.setItem(
      PROFILE_KEY,
      JSON.stringify({
        display_name: data.profile.display_name,
        updated_at: nowIso()
      })
    );
  }
  return Array.isArray(data.entries) ? data.entries : [];
}

/**
 * Normalize source strings for catalog matching (trim + collapse ~ home).
 * @param {string} source
 * @returns {string}
 */
export function normalizeCatalogSource(source) {
  return String(source || '').trim();
}

/**
 * Find a previously analyzed catalog entry for this source path/URL.
 * Matches exact stored source first, then case-insensitive fallback.
 * @param {string} source
 * @param {'local' | 'github'} [sourceType='local']
 * @returns {Promise<CatalogEntry | null>}
 */
export async function findCatalogEntryBySource(source, sourceType = 'local') {
  const needle = normalizeCatalogSource(source);
  if (!needle) return null;
  const type = sourceType === 'github' ? 'github' : 'local';
  try {
    const entries = await listCatalog(needle);
    const exact = entries.find(
      (e) => e.source_type === type && normalizeCatalogSource(e.source) === needle
    );
    if (exact) return exact;
    const loose = entries.find(
      (e) =>
        e.source_type === type &&
        normalizeCatalogSource(e.source).toLowerCase() === needle.toLowerCase()
    );
    return loose ?? null;
  } catch {
    return null;
  }
}

/**
 * Open a cached analysis: updates last_opened_at and returns the stored model.
 * @param {string} id
 * @returns {Promise<{ entry: CatalogEntry, model: object }>}
 */
export async function openCatalogEntry(id) {
  const res = await fetch(`/api/catalog/${encodeURIComponent(id)}/open`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Could not open catalog entry (${res.status})`);
  }
  return res.json();
}

/**
 * @param {string} id
 * @returns {Promise<void>}
 */
export async function removeCatalogEntry(id) {
  const res = await fetch(`/api/catalog/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`Could not remove catalog entry (${res.status})`);
  }
}

/** @returns {Promise<void>} */
export async function clearCatalog() {
  const res = await fetch('/api/catalog', { method: 'DELETE' });
  if (!res.ok) {
    throw new Error(`Could not clear catalog (${res.status})`);
  }
}

/**
 * @param {string} iso
 * @returns {string}
 */
export function formatViewedAt(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return iso;
  }
}

/**
 * Relative "Opened 3h ago" style label for cards.
 * @param {string} iso
 * @returns {string}
 */
export function formatRelativeOpened(iso) {
  if (!iso) return 'Never opened';
  try {
    const then = new Date(iso).getTime();
    const diffMs = Date.now() - then;
    if (Number.isNaN(then)) return formatViewedAt(iso);
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'Opened just now';
    if (mins < 60) return `Opened ${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `Opened ${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 14) return `Opened ${days}d ago`;
    return `Opened ${formatViewedAt(iso)}`;
  } catch {
    return formatViewedAt(iso);
  }
}
