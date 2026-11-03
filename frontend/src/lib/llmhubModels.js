/** Shared LLMHub model list cache — survives SourceBar remounts. */

/** @type {{ options: string[], preferred: string, status: string } | null} */
let cachedModels = null;
/** @type {Promise<{ options: string[], preferred: string, status: string }> | null} */
let modelsInflight = null;

function statusFromPayload(data, opts) {
  if (data.live_status === 'ok') return `LLMHub online · ${opts.length} models`;
  if (data.live_status === 'unreachable') return 'LLMHub unreachable — using .env model list';
  if (data.live_status === 'error') return 'LLMHub error — using .env model list';
  return opts.length ? `${opts.length} models from .env` : 'No models configured in .env';
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
      cachedModels = {
        options: opts,
        preferred,
        status: statusFromPayload(data, opts)
      };
      return cachedModels;
    } catch {
      cachedModels = {
        options: [],
        preferred: '',
        status: 'Could not load /api/llmhub/models'
      };
      return cachedModels;
    } finally {
      modelsInflight = null;
    }
  })();
  return modelsInflight;
}
