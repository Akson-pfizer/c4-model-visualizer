// Cross-platform keyboard shortcut matcher and catalog supporting both
// macOS (⌘ Cmd / ⌥ Option / ⇧ Shift) and Windows / Linux (Ctrl / Alt / Shift).

export const SHORTCUT_GROUPS = [
  {
    group: 'History & Clipboard (Canvas & Navigation)',
    items: [
      {
        action: 'Undo last canvas edit or layer navigation',
        mac: '⌘ + Z',
        win: 'Ctrl + Z'
      },
      {
        action: 'Redo last undone action',
        mac: '⌘ + Y  or  ⌘ + ⇧ + Z',
        win: 'Ctrl + Y  or  Ctrl + Shift + Z'
      },
      {
        action: 'Copy selected component(s) / node JSON',
        mac: '⌘ + C',
        win: 'Ctrl + C'
      },
      {
        action: 'Cut selected component(s) (Developer canvas)',
        mac: '⌘ + X',
        win: 'Ctrl + X'
      },
      {
        action: 'Paste copied component(s) onto canvas',
        mac: '⌘ + V',
        win: 'Ctrl + V'
      },
      {
        action: 'Duplicate selected component(s)',
        mac: '⌘ + D',
        win: 'Ctrl + D'
      },
      {
        action: 'Select all components on canvas',
        mac: '⌘ + A',
        win: 'Ctrl + A'
      },
      {
        action: 'Delete / remove selected component(s) or edge(s)',
        mac: 'Delete  or  ⌫ Backspace',
        win: 'Delete  or  Backspace'
      }
    ]
  },
  {
    group: 'C4 Layer Drill-Down & Hierarchy Navigation',
    items: [
      {
        action: 'Switch directly to Context / Container / Component / Code layer',
        mac: '1 / 2 / 3 / 4  (or ⌥ + 1..4)',
        win: '1 / 2 / 3 / 4  (or Alt + 1..4)'
      },
      {
        action: 'Drill down into next C4 layer for selected component',
        mac: 'Enter  or  ⌥ + ↓',
        win: 'Enter  or  Alt + ↓'
      },
      {
        action: 'Go up to upper C4 layer',
        mac: '⌥ + ↑  or  [',
        win: 'Alt + ↑  or  ['
      },
      {
        action: 'Go to next C4 layer',
        mac: ']',
        win: ']'
      },
      {
        action: 'Toggle Layer View ↔ Hierarchy Tree View',
        mac: 'T',
        win: 'T'
      },
      {
        action: 'Clear selection / Reset zoomed-in focus / Close modal',
        mac: 'Esc',
        win: 'Esc'
      },
      {
        action: 'Open / close Keyboard Shortcuts Reference',
        mac: '?  or  ⌘ + /',
        win: '?  or  Ctrl + /'
      }
    ]
  }
];

/**
 * Returns true if the keyboard event originated inside an editable input,
 * textarea, select, or contentEditable element where native typing shortcuts apply.
 */
export function isEditableTarget(target) {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (target.isContentEditable) return true;
  return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'));
}

/**
 * Normalizes a KeyboardEvent into a cross-platform semantic command (macOS ⌘ or Windows/Linux Ctrl).
 * Returns null if the event does not match a known shortcut.
 */
export function matchShortcutCommand(event) {
  if (!event) return null;

  const mod = event.metaKey || event.ctrlKey;
  const shift = event.shiftKey;
  const alt = event.altKey;
  const key = (event.key || '').toLowerCase();

  // Allow Esc and Cmd/Ctrl + / even inside inputs
  if (event.key === 'Escape') {
    return 'escape';
  }
  if (mod && (event.key === '/' || event.key === '?')) {
    return 'toggle-help';
  }

  // Do not hijack typing/clipboard inside text inputs
  if (isEditableTarget(event.target)) {
    return null;
  }

  // Undo: Cmd+Z (Mac) or Ctrl+Z (Windows/Linux) without Shift
  if (mod && !shift && !alt && key === 'z') {
    return 'undo';
  }

  // Redo: Cmd+Y / Ctrl+Y OR Cmd+Shift+Z / Ctrl+Shift+Z
  if (mod && !alt && (key === 'y' || (shift && key === 'z'))) {
    return 'redo';
  }

  // Copy: Cmd+C / Ctrl+C
  if (mod && !shift && !alt && key === 'c') {
    return 'copy';
  }

  // Cut: Cmd+X / Ctrl+X
  if (mod && !shift && !alt && key === 'x') {
    return 'cut';
  }

  // Paste: Cmd+V / Ctrl+V
  if (mod && !shift && !alt && key === 'v') {
    return 'paste';
  }

  // Duplicate: Cmd+D / Ctrl+D
  if (mod && !shift && !alt && key === 'd') {
    return 'duplicate';
  }

  // Select All: Cmd+A / Ctrl+A
  if (mod && !shift && !alt && key === 'a') {
    return 'select-all';
  }

  // Delete / Backspace
  if (!mod && !alt && (event.key === 'Delete' || event.key === 'Backspace')) {
    return 'delete';
  }

  // Help modal: ?
  if (!mod && !alt && event.key === '?') {
    return 'toggle-help';
  }

  // Layer selection: 1..4 or Alt+1..4
  if (!mod && ['1', '2', '3', '4'].includes(key)) {
    return `layer-${key}`;
  }

  // Drill down into selected node's next layer: Enter or Alt+ArrowDown
  if ((!mod && !alt && event.key === 'Enter') || (alt && event.key === 'ArrowDown')) {
    return 'drill-down';
  }

  // Go up to upper layer: Alt+ArrowUp or [
  if ((alt && event.key === 'ArrowUp') || (!mod && !alt && event.key === '[')) {
    return 'layer-up';
  }

  // Go to next layer: ]
  if (!mod && !alt && event.key === ']') {
    return 'layer-down';
  }

  // Toggle Layer / Tree view: T
  if (!mod && !alt && !shift && key === 't') {
    return 'toggle-tree';
  }

  return null;
}

/**
 * Strips non-serializable function callbacks from Svelte Flow nodes so snapshots
 * can be safely cloned for undo/redo history and clipboard storage.
 */
export function cloneDiagramSnapshot(nodes = [], edges = []) {
  const cleanNodes = nodes.map((n) => {
    const cleanData = {};
    for (const [k, v] of Object.entries(n.data ?? {})) {
      if (typeof v !== 'function') {
        cleanData[k] = v;
      }
    }
    return structuredClone({
      ...n,
      data: cleanData
    });
  });

  const cleanEdges = edges.map((e) => structuredClone(e));
  return { nodes: cleanNodes, edges: cleanEdges };
}
