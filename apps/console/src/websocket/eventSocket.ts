/**
 * ULTRONE Live Event Stream WebSocket Client
 * Connects to the FastAPI backend event bus and dispatches real-time entity updates,
 * sensor observations, telemetry deltas, and alert notifications.
 */

type EventHandler = (event: any) => void;

export class UltroneEventSocket {
  private url: string;
  private socket: WebSocket | null = null;
  private reconnectInterval: number = 3000;
  private handlers: Set<EventHandler> = new Set();
  private isConnecting: boolean = false;

  constructor(url: string = 'ws://localhost:8000/ws/world') {
    this.url = url;
  }

  public connect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
    if (this.isConnecting) return;

    this.isConnecting = true;
    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.isConnecting = false;
        console.log(`[EventSocket] Connected to ULTRONE event bus at ${this.url}`);
      };

      this.socket.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          this.handlers.forEach((h) => h(data));
        } catch (e) {
          console.error('[EventSocket] Failed to parse event payload:', e);
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.socket.onerror = () => {
        this.isConnecting = false;
      };
    } catch {
      this.isConnecting = false;
    }
  }

  public subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  public send(payload: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.handlers.clear();
  }
}

export const eventSocket = new UltroneEventSocket();
