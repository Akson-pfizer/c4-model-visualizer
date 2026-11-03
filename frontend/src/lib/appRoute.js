/**
 * Lightweight path routing for Catalog ↔ Orthos Studio (no router dependency).
 *
 *   /          → catalog (landing)
 *   /catalog   → catalog
 *   /studio    → Orthos Studio
 */

/** @typedef {'catalog' | 'studio'} AppView */

/**
 * @param {string} [pathname]
 * @returns {AppView}
 */
export function viewFromPath(pathname = window.location.pathname) {
  const path = (pathname || '/').replace(/\/+$/, '') || '/';
  if (path === '/studio') return 'studio';
  return 'catalog';
}

/**
 * @param {AppView} view
 * @returns {string}
 */
export function pathForView(view) {
  return view === 'studio' ? '/studio' : '/';
}

/**
 * @param {AppView} view
 * @param {{ replace?: boolean }} [opts]
 */
export function navigateToView(view, { replace = false } = {}) {
  const next = pathForView(view);
  const current = window.location.pathname.replace(/\/+$/, '') || '/';
  if (current === next) return;
  const url = `${next}${window.location.search}${window.location.hash}`;
  if (replace) {
    window.history.replaceState({ appView: view }, '', url);
  } else {
    window.history.pushState({ appView: view }, '', url);
  }
}

/**
 * @param {AppView} view
 */
export function titleForView(view) {
  return view === 'studio' ? 'Orthos Studio · Orthos' : 'Catalog · Orthos';
}
