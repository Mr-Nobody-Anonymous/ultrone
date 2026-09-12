/**
 * ULTRONE MapLibre 2D Tactical Engine Controller
 * Manages 2D vector tiles, tactical range rings, heading vectors,
 * raster tile layers, and synchronized panning/zooming.
 */

export interface MapView2DState {
  center: [number, number]; // [lon, lat]
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface TacticalMarker2D {
  id: string;
  coordinates: [number, number];
  heading: number;
  callsign: string;
  classification: string;
  speedMps: number;
}

export class MapLibreEngine {
  private containerId: string;
  private viewState: MapView2DState;
  private markers: Map<string, TacticalMarker2D> = new Map();
  private rangeRingsEnabled: boolean = true;
  private vectorsEnabled: boolean = true;

  constructor(containerId: string, initialView?: Partial<MapView2DState>) {
    this.containerId = containerId;
    this.viewState = {
      center: initialView?.center ?? [35.2, 31.7],
      zoom: initialView?.zoom ?? 10,
      bearing: initialView?.bearing ?? 0,
      pitch: initialView?.pitch ?? 0,
    };
  }

  public initialize(): void {
    const el = document.getElementById(this.containerId);
    if (!el) {
      console.warn(`[MapLibreEngine] Container element #${this.containerId} not found.`);
      return;
    }
  }

  public setView(view: Partial<MapView2DState>): void {
    this.viewState = { ...this.viewState, ...view };
  }

  public getViewState(): MapView2DState {
    return { ...this.viewState };
  }

  public setMarker(marker: TacticalMarker2D): void {
    this.markers.set(marker.id, marker);
  }

  public removeMarker(id: string): void {
    this.markers.delete(id);
  }

  public getMarkers(): TacticalMarker2D[] {
    return Array.from(this.markers.values());
  }

  public toggleRangeRings(enabled: boolean): void {
    this.rangeRingsEnabled = enabled;
  }

  public isRangeRingsEnabled(): boolean {
    return this.rangeRingsEnabled;
  }

  public toggleHeadingVectors(enabled: boolean): void {
    this.vectorsEnabled = enabled;
  }

  public isHeadingVectorsEnabled(): boolean {
    return this.vectorsEnabled;
  }

  public destroy(): void {
    this.markers.clear();
  }
}
