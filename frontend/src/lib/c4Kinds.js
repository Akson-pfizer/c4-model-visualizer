// Visual + semantic metadata for every C4 element "kind" used across the demo layers.
// Pastel fills stay inside Pfizer Brand Identity 2.0 (Blue 03/05/10, Cyan 10/30/50,
// Teal, Lavender). Shape + stereotype still carry the primary type distinction.
export const KIND_META = {
  person: {
    stereotype: 'Person',
    shape: 'pill',
    bg: '#E8F2FF' /* Blue 10 */,
    fg: '#000067' /* Blue 90 */,
    border: '#68D1FF' /* Cyan 30 */
  },
  system: {
    stereotype: 'Software System',
    shape: 'rect',
    bg: '#ECF6FF' /* Blue 03 */,
    fg: '#000067',
    border: '#0095FF' /* Cyan 50 */
  },
  systemExternal: {
    stereotype: 'Software System · external',
    shape: 'rect-dashed',
    bg: '#EEF5FB' /* Blue 05 */,
    fg: '#000067',
    border: '#AEE3FF' /* Cyan 10 */
  },
  container: {
    stereotype: 'Container',
    shape: 'rect',
    bg: '#AEE3FF' /* Cyan 10 */,
    fg: '#000067',
    border: '#0095FF' /* Cyan 50 */
  },
  containerDb: {
    stereotype: 'Container · database',
    shape: 'rect-db',
    bg: '#D7F7F3' /* soft Teal tint */,
    fg: '#000067',
    border: '#00B7A5' /* Teal */
  },
  containerExternal: {
    stereotype: 'Container · external',
    shape: 'rect-dashed',
    bg: '#EEF5FB',
    fg: '#000067',
    border: '#AEE3FF'
  },
  component: {
    stereotype: 'Component',
    shape: 'rect-accent',
    bg: '#E8F2FF' /* Blue 10 */,
    fg: '#000067',
    border: '#68D1FF' /* Cyan 30 */
  },
  codeInterface: {
    stereotype: 'Interface',
    shape: 'rect-code',
    bg: '#ECF6FF',
    fg: '#0000C9' /* Blue 70 */,
    border: '#68D1FF'
  },
  codeClass: {
    stereotype: 'Class',
    shape: 'rect-code',
    bg: '#EEF5FB',
    fg: '#000067',
    border: '#0095FF'
  },
  codeEnum: {
    stereotype: 'Enum',
    shape: 'rect-code',
    bg: '#F3EDFF' /* soft Lavender tint */,
    fg: '#000067',
    border: '#A68AFF' /* Lavender — sparingly */
  }
};

export function kindMeta(kind) {
  return KIND_META[kind] ?? KIND_META.container;
}
