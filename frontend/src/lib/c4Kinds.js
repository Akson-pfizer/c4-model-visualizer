// Visual + semantic metadata for every C4 element "kind" used across the demo layers.
// Color is a secondary signal only — the stereotype label and shape family carry the
// type distinction too, so nothing here is color-only (WCAG / Gestalt guidance).
export const KIND_META = {
  person: {
    stereotype: 'Person',
    shape: 'pill',
    bg: 'var(--blue-900)',
    fg: '#ffffff',
    border: 'var(--blue-900)'
  },
  system: {
    stereotype: 'Software System',
    shape: 'rect',
    bg: 'var(--blue-700)',
    fg: '#ffffff',
    border: 'var(--blue-700)'
  },
  systemExternal: {
    stereotype: 'Software System · external',
    shape: 'rect-dashed',
    bg: 'var(--surface-sunken)',
    fg: 'var(--text-muted)',
    border: 'var(--border-strong)'
  },
  container: {
    stereotype: 'Container',
    shape: 'rect',
    bg: 'var(--blue-600)',
    fg: '#ffffff',
    border: 'var(--blue-600)'
  },
  containerDb: {
    stereotype: 'Container · database',
    shape: 'rect-db',
    bg: 'var(--blue-500)',
    fg: '#ffffff',
    border: 'var(--blue-500)'
  },
  containerExternal: {
    stereotype: 'Container · external',
    shape: 'rect-dashed',
    bg: 'var(--surface-sunken)',
    fg: 'var(--text-muted)',
    border: 'var(--border-strong)'
  },
  component: {
    stereotype: 'Component',
    shape: 'rect-accent',
    bg: 'var(--blue-50)',
    fg: 'var(--blue-900)',
    border: 'var(--blue-300)'
  },
  codeInterface: {
    stereotype: 'Interface',
    shape: 'rect-code',
    bg: '#ffffff',
    fg: 'var(--blue-700)',
    border: 'var(--blue-300)'
  },
  codeClass: {
    stereotype: 'Class',
    shape: 'rect-code',
    bg: '#ffffff',
    fg: 'var(--text)',
    border: 'var(--border-strong)'
  },
  codeEnum: {
    stereotype: 'Enum',
    shape: 'rect-code',
    bg: '#ffffff',
    fg: 'var(--text-muted)',
    border: 'var(--border)'
  }
};

export function kindMeta(kind) {
  return KIND_META[kind] ?? KIND_META.container;
}
