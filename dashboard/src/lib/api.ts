const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Wallet {
  id: number;
  address: string;
  alias: string | null;
  enabled: boolean;
  created_at: string;
}

export interface Trade {
  id: string;
  wallet: string;
  wallet_alias?: string;
  market_id: string;
  market_title?: string;
  side: 'YES' | 'NO';
  size: number;
  price: number;
  timestamp: string;
  decision?: 'COPY' | 'SKIP' | 'WAIT';
  executed: boolean;
  pnl?: number;
}

export interface Status {
  mode: 'paper' | 'live' | 'paused';
  is_running: boolean;
  wallets_count: number;
  daily_pnl: number;
  open_exposure: number;
  total_trades: number;
}

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  components?: {
    database: string;
    cache: string;
  };
  message?: string;
}

export interface RiskLimits {
  max_daily_loss: number;
  max_total_exposure: number;
  max_single_trade: number;
  max_slippage: number;
}

export interface Settings {
  trading_mode: string;
  auto_trade: boolean;
  max_position_size: number;
  max_daily_exposure: number;
  ai_enabled: boolean;
  confidence_threshold: number;
  min_probability: number;
  max_probability: number;
  daily_loss_limit: number;
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Health
  getHealth: () => fetchAPI<HealthStatus>('/health'),
  getHealthDetailed: () => fetchAPI<HealthStatus>('/health/detailed'),

  // Wallets
  getWallets: () => fetchAPI<Wallet[]>('/wallets'),
  addWallet: (address: string, alias?: string) =>
    fetchAPI<Wallet>('/wallets', {
      method: 'POST',
      body: JSON.stringify({ address, alias }),
    }),
  removeWallet: (address: string) =>
    fetchAPI<void>(`/wallets/${address}`, { method: 'DELETE' }),

  // Status
  getStatus: () => fetchAPI<Status>('/status'),
  setMode: (mode: 'paper' | 'live' | 'paused') =>
    fetchAPI<void>('/status/mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

  // Trades
  getTrades: (limit?: number) => fetchAPI<Trade[]>(`/trades?limit=${limit || 50}`),

  // Settings
  getSettings: () => fetchAPI<Settings>('/settings'),
  updateSettings: (settings: Partial<Settings>) =>
    fetchAPI<Settings>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),
};

// SWR fetcher
export const fetcher = <T>(url: string): Promise<T> => fetchAPI<T>(url);
