/**
 * Zustand store — single source of truth for the desk UI.
 */

import { create } from 'zustand';

export type AgentName =
  | 'SCOUT'
  | 'CARTOGRAPHER'
  | 'HUNTER'
  | 'ANALYST'
  | 'GUARDIAN'
  | 'EXECUTIONER'
  | 'CHRONICLER';

export interface AgentState {
  name: AgentName;
  status: string;
  summary: string;
  confidence: number;
  latencyMs: number;
  data?: Record<string, any>;
  updatedAt?: string;
}

export interface Toast {
  id: number;
  title: string;
  body?: string;
  tone: 'cyan' | 'rose' | 'emerald' | 'amber' | 'violet';
}

export type ViewTab = 'CONSTELLATION' | 'CHART' | 'SIGNALS' | 'BACKTEST' | 'JOURNAL' | 'SETTINGS';

export interface PositionState {
  id: string;
  instrument: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  lot_size: number;
  unrealized_pnl: number;
  state: string;
}

interface AppState {
  // navigation & layout
  activeTab: ViewTab;
  setActiveTab: (t: ViewTab) => void;
  showIntro: boolean;
  setShowIntro: (v: boolean) => void;
  showWelcome: boolean;
  setShowWelcome: (v: boolean) => void;
  proMode: boolean;
  toggleProMode: () => void;
  sound: boolean;
  toggleSound: () => void;
  tourStep: number; // -1 = done
  setTourStep: (n: number) => void;

  // backend state
  wsConnected: boolean;
  setWsConnected: (v: boolean) => void;
  agents: Record<AgentName, AgentState>;
  upsertAgent: (name: AgentName, patch: Partial<AgentState>) => void;
  activeAgent: AgentName | null;
  setActiveAgent: (a: AgentName | null) => void;

  account: { balance: number; equity: number; profit: number; drawdown: number; daily_drawdown: number } | null;
  setAccount: (a: any) => void;
  mode: string;
  setMode: (m: string) => void;
  demoBanner: boolean;
  setDemoBanner: (v: boolean) => void;
  mt5Status: Record<string, any> | null;
  setMt5Status: (v: Record<string, any> | null) => void;
  positions: PositionState[];
  setPositions: (p: PositionState[]) => void;
  session: string;
  setSession: (s: string) => void;

  // signals & journal
  lastDecision: Record<string, any> | null;
  setLastDecision: (d: Record<string, any> | null) => void;
  journalRefresh: number;
  bumpJournal: () => void;

  // toasts
  toasts: Toast[];
  pushToast: (t: Omit<Toast, 'id'>) => void;
  dismissToast: (id: number) => void;

  // demo scenario playback
  sweepPlaying: boolean;
  setSweepPlaying: (v: boolean) => void;
  sweepStep: number; // 0..4
  setSweepStep: (n: number) => void;
}

const initialAgents = (): Record<AgentName, AgentState> =>
  (['SCOUT', 'CARTOGRAPHER', 'HUNTER', 'ANALYST', 'GUARDIAN', 'EXECUTIONER', 'CHRONICLER'] as AgentName[]).reduce(
    (acc, name) => {
      acc[name] = { name, status: 'IDLE', summary: 'Awaiting first cycle…', confidence: 0, latencyMs: 0 };
      return acc;
    },
    {} as Record<AgentName, AgentState>,
  );

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'CONSTELLATION',
  setActiveTab: (activeTab) => set({ activeTab }),
  showIntro: typeof window !== 'undefined' ? !window.localStorage.getItem('qp-intro-seen') : true,
  setShowIntro: (showIntro) => set({ showIntro }),
  showWelcome: false,
  setShowWelcome: (showWelcome) => set({ showWelcome }),
  proMode: typeof window !== 'undefined' ? window.localStorage.getItem('qp-pro') === '1' : false,
  toggleProMode: () =>
    set((s) => {
      const next = !s.proMode;
      window.localStorage.setItem('qp-pro', next ? '1' : '0');
      return { proMode: next };
    }),
  sound: false,
  toggleSound: () => set((s) => ({ sound: !s.sound })),
  tourStep: typeof window !== 'undefined' && !window.localStorage.getItem('qp-intro-seen') ? 0 : -1,
  setTourStep: (tourStep) => set({ tourStep }),

  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),
  agents: initialAgents(),
  upsertAgent: (name, patch) =>
    set((s) => ({ agents: { ...s.agents, [name]: { ...s.agents[name], ...patch } } })),
  activeAgent: null,
  setActiveAgent: (activeAgent) => set({ activeAgent }),

  account: null,
  setAccount: (account) =>
    set({
      account: account
        ? {
            balance: account.balance ?? 0,
            equity: account.equity ?? 0,
            profit: account.profit ?? 0,
            drawdown: account.drawdown ?? 0,
            daily_drawdown: account.daily_drawdown ?? 0,
          }
        : null,
    }),
  mode: 'DEMO',
  setMode: (mode) => set({ mode }),
  demoBanner: true,
  setDemoBanner: (demoBanner) => set({ demoBanner }),
  mt5Status: null,
  setMt5Status: (mt5Status) => set({ mt5Status }),
  positions: [],
  setPositions: (positions) => set({ positions }),
  session: 'ASIAN',
  setSession: (session) => set({ session }),

  lastDecision: null,
  setLastDecision: (lastDecision) => set({ lastDecision }),
  journalRefresh: 0,
  bumpJournal: () => set((s) => ({ journalRefresh: s.journalRefresh + 1 })),

  toasts: [],
  pushToast: (t) =>
    set((s) => ({ toasts: [...s.toasts.slice(-3), { ...t, id: Date.now() + Math.random() }] })),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),

  sweepPlaying: false,
  setSweepPlaying: (sweepPlaying) => set({ sweepPlaying }),
  sweepStep: 0,
  setSweepStep: (sweepStep) => set({ sweepStep }),
}));