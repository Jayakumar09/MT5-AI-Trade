/**
 * REST + WebSocket client for the QUANT PILOT backend.
 * WebSocket reconnects with exponential backoff; REST calls never throw raw
 * errors — they return a typed fallback and surface a friendly toast via the store.
 */

import { useAppStore } from '../store/useAppStore';

const API = ''; // same origin (vite proxy forwards /api, /ws, /health to :8000)
const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/events`;

export async function apiGet<T = any>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${API}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[api] GET ${path} failed:`, err);
    return fallback;
  }
}

export async function apiPost<T = any>(path: string, body?: unknown, fallback?: T): Promise<T | any> {
  try {
    const res = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[api] POST ${path} failed:`, err);
    useAppStore.getState().pushToast({ title: 'Request failed', body: 'Backend unreachable — is the API running on :8000?', tone: 'rose' });
    return fallback;
  }
}

export interface WsEvent {
  type: string;
  agent?: string;
  status?: string;
  summary?: string;
  confidence?: number;
  data?: Record<string, any>;
  ts?: string;
  [k: string]: any;
}

type Listener = (ev: WsEvent) => void;

class WsClient {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private retry = 0;
  private timer: number | null = null;
  private wantOpen = false;

  connect() {
    this.wantOpen = true;
    this.open();
  }

  disconnect() {
    this.wantOpen = false;
    if (this.timer) window.clearTimeout(this.timer);
    this.ws?.close();
    this.ws = null;
  }

  subscribe(fn: Listener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private open() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    try {
      this.ws = new WebSocket(WS_URL);
    } catch {
      this.scheduleRetry();
      return;
    }
    this.ws.onopen = () => {
      this.retry = 0;
      this.emit({ type: 'connection', status: 'open' });
    };
    this.ws.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        this.emit(parsed);
      } catch {
        /* ignore malformed frames */
      }
    };
    this.ws.onclose = () => {
      this.emit({ type: 'connection', status: 'closed' });
      this.scheduleRetry();
    };
    this.ws.onerror = () => {
      /* onclose fires afterwards */
    };
  }

  private scheduleRetry() {
    if (!this.wantOpen) return;
    this.retry = Math.min(this.retry + 1, 6);
    const delay = Math.min(1000 * 2 ** (this.retry - 1), 15000);
    this.timer = window.setTimeout(() => this.open(), delay);
  }

  private emit(ev: WsEvent) {
    this.listeners.forEach((fn) => {
      try { fn(ev); } catch (err) { console.warn('[ws] listener error', err); }
    });
  }
}

export const wsClient = new WsClient();