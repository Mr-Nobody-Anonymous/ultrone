/**
 * ULTRONE Three.js Simulation & Swarm Engine Controller
 * Manages 3D isometric physics rendering, particle swarms, and kinematic test vectors.
 */

export interface SimParticle {
  id: string;
  position: [number, number, number];
  velocity: [number, number, number];
  color: string;
  size: number;
}

export class ThreeJSSimEngine {
  private containerId: string;
  private particles: Map<string, SimParticle> = new Map();
  private isRunning: boolean = false;
  private animationFrameId: number | null = null;

  constructor(containerId: string) {
    this.containerId = containerId;
  }

  public initialize(): void {
    const el = document.getElementById(this.containerId);
    if (!el) {
      console.warn(`[ThreeJSSimEngine] Container element #${this.containerId} not found.`);
      return;
    }
  }

  public addParticle(particle: SimParticle): void {
    this.particles.set(particle.id, particle);
  }

  public updateParticles(dt: number): void {
    for (const p of this.particles.values()) {
      p.position[0] += p.velocity[0] * dt;
      p.position[1] += p.velocity[1] * dt;
      p.position[2] += p.velocity[2] * dt;
    }
  }

  public getParticles(): SimParticle[] {
    return Array.from(this.particles.values());
  }

  public start(): void {
    this.isRunning = true;
  }

  public getIsRunning(): boolean {
    return this.isRunning;
  }

  public stop(): void {
    this.isRunning = false;
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  public destroy(): void {
    this.stop();
    this.particles.clear();
  }
}
