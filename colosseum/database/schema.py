SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS run_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  command TEXT NOT NULL,
  key TEXT NOT NULL,
  row_index INTEGER NOT NULL DEFAULT 0,
  value_json TEXT,
  units TEXT,
  artifact_path TEXT,
  status TEXT NOT NULL,
  timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_measurements_lookup
  ON measurements(domain, command, key);

CREATE TABLE IF NOT EXISTS verifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  command TEXT NOT NULL,
  key TEXT NOT NULL,
  expected_json TEXT,
  actual_json TEXT,
  tolerance_json TEXT,
  compare_op TEXT,
  status TEXT NOT NULL,
  optional INTEGER NOT NULL DEFAULT 0,
  message TEXT,
  description TEXT,
  timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  source TEXT NOT NULL,
  message TEXT NOT NULL,
  timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  command TEXT NOT NULL,
  key TEXT NOT NULL DEFAULT '',
  result_json TEXT,
  status TEXT NOT NULL,
  optional INTEGER NOT NULL DEFAULT 0,
  message TEXT,
  cause TEXT NOT NULL DEFAULT '',
  timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_commands_lookup
  ON commands(domain, command, key);

CREATE TABLE IF NOT EXISTS provenance (
  section TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_requirements (
  verification_id INTEGER NOT NULL REFERENCES verifications(id),
  requirement_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  PRIMARY KEY (verification_id, ordinal)
);

CREATE TABLE IF NOT EXISTS run_result (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  kind TEXT NOT NULL,
  overall_result TEXT NOT NULL,
  exit_code INTEGER NOT NULL,
  completed_at TEXT NOT NULL,
  format_version INTEGER NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suite_slot_results (
  slot_id INTEGER PRIMARY KEY,
  phase TEXT NOT NULL,
  script TEXT NOT NULL,
  output_directory TEXT NOT NULL,
  test_index INTEGER,
  repeat_index INTEGER,
  cycle_index INTEGER,
  affects_suite_result INTEGER NOT NULL,
  overall_result TEXT,
  exit_code INTEGER,
  payload_json TEXT NOT NULL
);
"""
