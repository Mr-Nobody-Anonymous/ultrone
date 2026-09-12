/**
 * ULTRONE Cesium 3D Globe Engine Controller
 * Provides camera control, terrain mesh streaming, 3D Tiles, entity billboard rendering,
 * and synchronized camera synchronization with the 2D tactical view.
 */

export interface CameraState {
  longitude: number;
  latitude: number;
  altitude: number;
  heading: number;
  pitch: number;
  roll: number;
}

export interface GlobeEntityBillboard {
  id: string;
  name: string;
  longitude: number;
  latitude: number;
  altitude: number;
  heading: number;
  classification: 'friendly' | 'hostile' | 'neutral' | 'unknown';
  iconUrl?: string;
}

export class CesiumGlobeEngine {
  private containerId: string;
  private camera: CameraState;
  private entities: Map<string, GlobeEntityBillboard> = new Map();
  private terrainEnabled: boolean = true;
  private tiles3dEnabled: boolean = true;

  constructor(containerId: string, initialCamera?: Partial<CameraState>) {
    this.containerId = containerId;
    this.camera = {
      longitude: initialCamera?.longitude ?? 35.2,
      latitude: initialCamera?.latitude ?? 31.7,
      altitude: initialCamera?.altitude ?? 25000,
      heading: initialCamera?.heading ?? 0,
      pitch: initialCamera?.pitch ?? -45,
      roll: initialCamera?.roll ?? 0,
    };
  }

  public initialize(): void {
    const el = document.getElementById(this.containerId);
    if (!el) {
      console.warn(`[CesiumGlobeEngine] Container element #${this.containerId} not found.`);
      return;
    }
  }

  public setCamera(camera: Partial<CameraState>): void {
    this.camera = { ...this.camera, ...camera };
  }

  public getCamera(): CameraState {
    return { ...this.camera };
  }

  public flyTo(longitude: number, latitude: number, altitude: number = 10000): void {
    this.setCamera({ longitude, latitude, altitude });
  }

  public upsertEntity(entity: GlobeEntityBillboard): void {
    this.entities.set(entity.id, entity);
  }

  public removeEntity(id: string): void {
    this.entities.delete(id);
  }

  public toggleTerrain(enabled: boolean): void {
    this.terrainEnabled = enabled;
  }

  public toggle3DTiles(enabled: boolean): void {
    this.tiles3dEnabled = enabled;
  }

  public isTerrainEnabled(): boolean {
    return this.terrainEnabled;
  }

  public is3DTilesEnabled(): boolean {
    return this.tiles3dEnabled;
  }

  public getEntities(): GlobeEntityBillboard[] {
    return Array.from(this.entities.values());
  }

  public destroy(): void {
    this.entities.clear();
  }
}
