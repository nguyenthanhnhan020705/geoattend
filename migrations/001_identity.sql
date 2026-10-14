CREATE TABLE geoattend.profiles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 username text NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9._-]{3,50}$'),
 full_name text NOT NULL CHECK (length(btrim(full_name)) BETWEEN 1 AND 200),
 password_hash text NOT NULL,
 role text NOT NULL CHECK (role IN ('USER','ADMIN')),
 is_active boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX single_admin ON geoattend.profiles(role) WHERE role='ADMIN';
CREATE TABLE geoattend.auth_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES geoattend.profiles(id),
 token_hash text NOT NULL UNIQUE,
 csrf_token text NOT NULL,
 expires_at timestamptz NOT NULL,
 revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX auth_user ON geoattend.auth_sessions(user_id);
CREATE INDEX auth_expiry ON geoattend.auth_sessions(expires_at);
CREATE TABLE geoattend.auth_attempts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 username text NOT NULL,
 attempted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX auth_attempt_window ON geoattend.auth_attempts(username,attempted_at);
