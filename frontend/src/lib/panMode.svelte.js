/**
 * Hand-tool state shared by every C4 canvas. Canvases remount on layer, view
 * and drill-down changes, so the toggle lives here instead of in each canvas.
 */
export const panTool = $state({ on: false });

export function togglePanTool() {
  panTool.on = !panTool.on;
}
