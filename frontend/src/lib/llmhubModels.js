/** Shared LLMHub model list cache — survives SourceBar remounts. */

/**
 * @typedef {'online' | 'offline' | 'error' | 'local' | 'loading'} HubStatusKind
 * @typedef {{ options: string[], preferred: string, status: string, statusKind: HubStatusKind }} HubModelsCache
 */

/** @type {HubModelsCache | null} */
let cachedModels = null;
/** @type {Promise<HubModelsCache> | null} */
let modelsInflight = null;

/**
 * @param {any} data
 * @param {string[]} opts
 * @returns {{ status: string, statusKind: HubStatusKind }}
 */
function statusFromPayload(data, opts) {
  if (data.live_status === 'ok') {
    return {
      status: `LLMHub online · ${opts.length} models`,
      statusKind: 'online'
    };
  }
  if (data.live_status === 'unreachable') {
    return {
      status: 'LLMHub unreachable — using .env model list',
      statusKind: 'offline'
    };
  }
  if (data.live_status === 'error') {
    return {
      status: 'LLMHub error — using .env model list',
      statusKind: 'error'
    };
  }
  if (opts.length) {
    return {
      status: `${opts.length} models from .env`,
      statusKind: 'local'
    };
  }
  return {
    status: 'No models configured in .env',
    statusKind: 'error'
  };
}

export function getCachedModels() {
  return cachedModels;
}

export function loadLlmHubModels() {
  if (cachedModels) return Promise.resolve(cachedModels);
  if (modelsInflight) return modelsInflight;
  modelsInflight = (async () => {
    try {
      const res = await fetch('/api/llmhub/models');
      const data = await res.json().catch(() => ({}));
      const opts = Array.isArray(data.options) ? data.options : [];
      const preferred = data.default_medium || data.default_powerful || opts[0] || '';
      const meta = statusFromPayload(data, opts);
      cachedModels = {
        options: opts,
        preferred,
        status: meta.status,
        statusKind: meta.statusKind
      };
      return cachedModels;
    } catch {
      cachedModels = {
        options: [],
        preferred: '',
        status: 'Could not load /api/llmhub/models',
        statusKind: 'error'
      };
      return cachedModels;
    } finally {
      modelsInflight = null;
    }
  })();
  return modelsInflight;
}
