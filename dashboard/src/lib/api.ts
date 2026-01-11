// Only use localhost in development, otherwise require explicit config
const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

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
  wallet_count: number;
  daily_pnl: number;
  open_exposure: number;
  total_trades: number;
  emergency_stop?: boolean;
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
  starting_balance: number;
  max_slippage: number;
  copy_percentage: number;
}

export interface WalletDetail extends Wallet {
  scale_factor: number;
  max_trade_size: number | null;
  min_confidence: number;
  win_rate: number | null;
  avg_roi: number | null;
  total_trades: number;
  total_pnl: number | null;
}

export interface MarketFilter {
  id: number;
  filter_type: 'market_id' | 'category' | 'keyword';
  value: string;
  action: 'allow' | 'deny';
  created_at: string;
}

export interface MarketMapping {
  id: number;
  polymarket_id: string | null;
  kalshi_id: string | null;
  description: string | null;
  active: boolean;
  created_at: string;
}

export interface ArbitrageOpportunity {
  polymarket_id: string;
  kalshi_id: string;
  spread: number;
  direction: 'BUY_YES' | 'BUY_NO';
  poly_price: number;
  kalshi_price: number;
  confidence: number;
}

export interface ArbitrageScanResponse {
  opportunities: ArbitrageOpportunity[];
  scanned_at: string;
}

export interface Market {
  condition_id: string;
  question: string;
  description: string;
  end_date: string | null;
  resolution_date: string | null;
  active: boolean;
  closed: boolean;
  image?: string;
  icon?: string;
}

export interface Order {
  id: number;
  external_id: string | null;
  signal_id: string | null;
  market_id: string;
  side: 'BUY' | 'SELL';
  status: 'pending' | 'submitted' | 'filled' | 'partial' | 'failed' | 'cancelled';
  requested_size: number;
  filled_size: number;
  requested_price: number;
  filled_price: number | null;
  attempts: number;
  max_attempts: number;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
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

  // Emergency Stop
  emergencyStop: () => fetchAPI<{ success: boolean; message: string; emergency_stop: boolean }>('/emergency-stop', { method: 'POST' }),
  resumeTrading: () => fetchAPI<{ success: boolean; message: string; emergency_stop: boolean }>('/resume-trading', { method: 'POST' }),

  // Trades
  getTrades: (limit?: number) => fetchAPI<Trade[]>(`/trades?limit=${limit || 50}`),

  // Settings
  getSettings: () => fetchAPI<Settings>('/settings'),
  updateSettings: (settings: Partial<Settings>) =>
    fetchAPI<Settings>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  // Wallet Details
  getWalletDetail: (address: string) => fetchAPI<WalletDetail>(`/wallets/${address}`),
  updateWalletControls: (address: string, controls: { scale_factor?: number; max_trade_size?: number | null; min_confidence?: number }) =>
    fetchAPI<WalletDetail>(`/wallets/${address}/controls`, {
      method: 'PUT',
      body: JSON.stringify(controls),
    }),

  // Market Filters
  getFilters: () => fetchAPI<MarketFilter[]>('/filters'),
  addFilter: (filter: Omit<MarketFilter, 'id' | 'created_at'>) =>
    fetchAPI<MarketFilter>('/filters', {
      method: 'POST',
      body: JSON.stringify(filter),
    }),
  removeFilter: (id: number) =>
    fetchAPI<void>(`/filters/${id}`, { method: 'DELETE' }),

  // Market Mappings
  getMappings: () => fetchAPI<MarketMapping[]>('/arbitrage/mappings'),
  addMapping: (mapping: Omit<MarketMapping, 'id' | 'created_at'>) =>
    fetchAPI<MarketMapping>('/arbitrage/mappings', {
      method: 'POST',
      body: JSON.stringify(mapping),
    }),
  removeMapping: (id: number) =>
    fetchAPI<void>(`/arbitrage/mappings/${id}`, { method: 'DELETE' }),

  // Arbitrage
  getArbitrageOpportunities: () => fetchAPI<ArbitrageOpportunity[]>('/arbitrage/opportunities'),
  scanArbitrage: () => fetchAPI<ArbitrageScanResponse>('/arbitrage/scan', { method: 'POST' }),

  // Orders
  getOrders: (status?: string, limit?: number) =>
    fetchAPI<Order[]>(`/orders?${status ? `status=${status}&` : ''}limit=${limit || 50}`),
  cancelOrder: (id: number) =>
    fetchAPI<Order>(`/orders/${id}/cancel`, { method: 'POST' }),
};

// SWR fetcher
export const fetcher = <T>(url: string): Promise<T> => fetchAPI<T>(url);
