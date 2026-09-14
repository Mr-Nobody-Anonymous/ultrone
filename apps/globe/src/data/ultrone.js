// ULTRONE-owned wiring: standalone source + application overlay owner.
import {
  createUltroneLayer as createLayer,
  createUltroneSource,
} from '../layers/ultrone/index.js';
import {
  clearOverlaySource,
  setOverlayEntries,
  setOverlaySourceVisible,
} from '../overlays/worldOverlay.js';
export * from '../layers/ultrone/index.js';
/** Wire the standalone source and application overlay owner. */
export function createUltroneLayer({
  source = createUltroneSource(),
  overlayHost = {
    setEntries: setOverlayEntries,
    setVisible: setOverlaySourceVisible,
    clearSource: clearOverlaySource,
  },
} = {}) {
  return createLayer({ source, overlayHost });
}
export default createUltroneLayer();
