-- Minimal SQLite schema (local-only)
CREATE TABLE IF NOT EXISTS venue (id TEXT PRIMARY KEY, kind TEXT);
CREATE TABLE IF NOT EXISTS instrument (id TEXT PRIMARY KEY, symbol TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS account (id TEXT PRIMARY KEY, venue_id TEXT REFERENCES venue(id), nickname TEXT);
CREATE TABLE IF NOT EXISTS balance_snapshot (
  ts TEXT NOT NULL,
  account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  qty REAL NOT NULL,
  PRIMARY KEY (ts, account_id, instrument_id)
);
CREATE TABLE IF NOT EXISTS "order" (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  side TEXT CHECK (side IN ('buy','sell')),
  ord_type TEXT,
  qty REAL,
  px REAL,
  status TEXT
);
CREATE TABLE IF NOT EXISTS trade (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  order_id TEXT REFERENCES "order"(id),
  account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  side TEXT CHECK (side IN ('buy','sell')),
  qty REAL NOT NULL,
  px REAL NOT NULL,
  fee_qty REAL DEFAULT 0,
  fee_instrument_id TEXT REFERENCES instrument(id)
);
CREATE TABLE IF NOT EXISTS transfer (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  from_account_id TEXT REFERENCES account(id),
  to_account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  qty REAL NOT NULL,
  tx_hash TEXT
);
CREATE TABLE IF NOT EXISTS price (
  ts TEXT NOT NULL,
  instrument_id TEXT REFERENCES instrument(id),
  px REAL NOT NULL,
  source TEXT,
  PRIMARY KEY (ts, instrument_id)
);
CREATE TABLE IF NOT EXISTS lot (
  id TEXT PRIMARY KEY,
  open_ts TEXT NOT NULL,
  account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  open_qty REAL NOT NULL,
  open_px REAL NOT NULL,
  remaining_qty REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS lot_event (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  lot_id TEXT REFERENCES lot(id),
  trade_id TEXT REFERENCES trade(id),
  qty REAL NOT NULL,
  proceeds REAL NOT NULL,
  gain_loss REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS income (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  account_id TEXT REFERENCES account(id),
  instrument_id TEXT REFERENCES instrument(id),
  kind TEXT CHECK (kind IN ('funding','interest','dividend','staking')),
  qty REAL NOT NULL,
  fmv_usd REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS strategy_pnl (
  ts TEXT NOT NULL,
  strategy TEXT,
  realized_usd REAL DEFAULT 0,
  unrealized_usd REAL DEFAULT 0,
  fees_usd REAL DEFAULT 0,
  PRIMARY KEY (ts, strategy)
);
