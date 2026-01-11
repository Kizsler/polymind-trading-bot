# PolyMind Multi-User Platform Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform PolyMind from a single-user copy trading bot into a multi-tenant SaaS platform where each user gets their own bot instance, tracks their own stats, and manages their own wallets.

**Architecture:** Supabase for auth + database, per-user bot instances managed by a supervisor, Next.js dashboard with user-scoped data via row-level security.

**Tech Stack:** Next.js, Supabase (Auth + Postgres), FastAPI, Python bot supervisor

---

## 1. Architecture Overview

**Stack:**
- **Frontend:** Next.js dashboard (existing) + auth pages
- **Backend:** FastAPI (existing) + user-scoped endpoints
- **Database:** Supabase Postgres (replaces SQLite)
- **Auth:** Supabase Auth (Email, Discord, GitHub)
- **Bot:** One instance per user, managed by a supervisor process

**Data Flow:**
```
User signs up → Supabase Auth creates account
                    ↓
         User goes through onboarding
         (pick starting balance, optional custom wallets)
                    ↓
         Bot supervisor spawns user's bot instance
                    ↓
         Bot watches PolyMind wallets + user's custom wallets
                    ↓
         Trades stored in Supabase with user_id
                    ↓
         Dashboard shows only that user's data (RLS enforced)
```

---

## 2. Supabase Configuration

**Project URL:** `https://mfmtowyjxhpwamdbdjgv.supabase.co`

**Auth Providers:**
- Email/Password (enabled by default)
- Discord OAuth (requires Discord Developer app)
- GitHub OAuth (requires GitHub OAuth app)

---

## 3. Database Schema

```sql
-- User profiles (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    starting_balance DECIMAL(10,2) DEFAULT 1000 CHECK (starting_balance <= 10000),
    copy_percentage DECIMAL(3,2) DEFAULT 0.10,
    bot_status TEXT DEFAULT 'stopped' CHECK (bot_status IN ('running', 'paused', 'stopped')),
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PolyMind recommended wallets (shared, admin-managed)
CREATE TABLE recommended_wallets (
    id SERIAL PRIMARY KEY,
    address TEXT UNIQUE NOT NULL,
    alias TEXT NOT NULL,
    description TEXT,
    win_rate DECIMAL(5,2),
    total_trades INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User's selected recommended wallets
CREATE TABLE user_recommended_selections (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    wallet_id INTEGER REFERENCES recommended_wallets(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, wallet_id)
);

-- User's custom wallets
CREATE TABLE user_wallets (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    alias TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, address)
);

-- All trades (user-scoped)
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    wallet_address TEXT NOT NULL,
    market_id TEXT NOT NULL,
    market_title TEXT,
    side TEXT NOT NULL CHECK (side IN ('YES', 'NO')),
    size DECIMAL(10,2) NOT NULL,
    price DECIMAL(5,4) NOT NULL,
    pnl DECIMAL(10,2),
    executed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row-Level Security Policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_recommended_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;

-- Profiles: users can only access their own
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Recommended wallets: everyone can read
CREATE POLICY "Anyone can view recommended wallets" ON recommended_wallets FOR SELECT TO authenticated USING (true);

-- User selections: users manage their own
CREATE POLICY "Users manage own selections" ON user_recommended_selections FOR ALL USING (auth.uid() = user_id);

-- User wallets: users manage their own
CREATE POLICY "Users manage own wallets" ON user_wallets FOR ALL USING (auth.uid() = user_id);

-- Trades: users see only their own
CREATE POLICY "Users view own trades" ON trades FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can insert trades" ON trades FOR INSERT WITH CHECK (true);
```

---

## 4. User Onboarding Flow

**Step 1: Welcome**
- "Welcome to PolyMind! Let's set up your paper trading account."

**Step 2: Starting Balance**
- Options: $100, $500, $1,000, $5,000, $10,000
- Default: $1,000

**Step 3: Wallet Selection**
- Show PolyMind recommended wallets (pre-selected)
- Option to add custom wallet addresses
- Each wallet shows win rate and description

**Step 4: Ready**
- "Your bot is starting! Watch your dashboard for trades."
- Redirect to dashboard

---

## 5. Dashboard Pages

```
/login          - Auth page (Email, Discord, GitHub buttons)
/onboarding     - First-time setup wizard (4 steps)
/dashboard      - Main dashboard (existing, now user-scoped)
/settings       - User settings & wallet management
```

**Middleware Protection:**
- All pages except `/login` require authentication
- Check Supabase session, redirect to `/login` if none
- Check `onboarding_completed`, redirect to `/onboarding` if false

---

## 6. Settings Page Structure

```
Settings
├── Profile
│   ├── Display name
│   └── Reset paper account (resets balance and trades)
├── Trading
│   ├── Copy percentage slider (1-100%)
│   └── Starting balance (for reset)
├── Wallets
│   ├── PolyMind Recommended (toggle each on/off)
│   └── My Custom Wallets (add/remove addresses)
└── Account
    ├── Connected logins (Discord, GitHub status)
    └── Sign out
```

---

## 7. Bot Supervisor Architecture

**Supervisor Process:**
- Single long-running process
- Manages all user bot instances
- Polls database for users with `bot_status = 'running'`
- Spawns/stops bot workers as needed

**Per-User Bot Worker:**
- Watches that user's selected wallets
- Shares market data cache with other workers
- Writes trades to Supabase with user_id
- Handles PnL calculation on resolution

**Lifecycle:**
- User completes onboarding → bot_status = 'running'
- User clicks "Stop Bot" → bot_status = 'paused'
- Supervisor detects change → stops worker
- User clicks "Start Bot" → bot_status = 'running'
- Supervisor detects change → spawns worker

---

## 8. API Changes

**New Endpoints:**
- `POST /api/auth/callback` - Handle OAuth redirects
- `GET /api/profile` - Get current user profile
- `PUT /api/profile` - Update profile settings
- `GET /api/wallets` - Get user's wallet selections
- `POST /api/wallets` - Add custom wallet
- `DELETE /api/wallets/:id` - Remove custom wallet
- `PUT /api/wallets/recommended/:id` - Toggle recommended wallet

**Modified Endpoints:**
- `GET /api/trades` - Now filtered by user_id
- `GET /api/status` - Now returns user's bot status
- `POST /api/start` - Starts user's bot
- `POST /api/stop` - Stops user's bot

---

## 9. Environment Variables

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://mfmtowyjxhpwamdbdjgv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# OAuth (to be configured)
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

---

## 10. Implementation Order

1. **Database Setup** - Create tables in Supabase, enable RLS
2. **Auth Integration** - Add Supabase auth to Next.js, create login page
3. **Onboarding Flow** - Build 4-step wizard, save to profiles table
4. **Dashboard Auth** - Protect routes, fetch user-scoped data
5. **Settings Page** - Build wallet management UI
6. **Bot Supervisor** - Refactor bot to multi-user architecture
7. **OAuth Setup** - Add Discord and GitHub providers
8. **Testing** - End-to-end flow with multiple users

---

## 11. Future Enhancements (Post-MVP)

- **Live Trading (Option A):** Connect user's Polymarket wallet
- **Live Trading (Option B):** Custodial trading (legal review needed)
- **Payments:** Stripe integration for premium features
- **Leaderboard:** Anonymous performance rankings
- **Social:** Share trade ideas, follow top performers
