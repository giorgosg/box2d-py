-- Scenarios, addressed by the hash of their own source.
--
-- Nothing here is mutable: an id is derived from the content, so a row can be
-- inserted and read but never updated. That is what lets a response be cached
-- forever, and it is why there is no delete.

CREATE TABLE IF NOT EXISTS scenarios (
  -- The 64 hex characters of the SHA-256 of the source's UTF-8 bytes.
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  -- Bytes rather than characters, so it matches what the size cap measured.
  bytes INTEGER NOT NULL,
  -- Unix milliseconds. SQLite has no date type, and an integer sorts.
  created_at INTEGER NOT NULL
);

-- For listing what has arrived lately, which is the one query that is not by id.
CREATE INDEX IF NOT EXISTS idx_scenarios_created_at ON scenarios (created_at DESC);
