CREATE TABLE geoattend.user_avatars (
 user_id uuid PRIMARY KEY REFERENCES geoattend.profiles(id) ON DELETE CASCADE,
 content bytea NOT NULL CHECK (octet_length(content) BETWEEN 1 AND 5000000),
 media_type text NOT NULL CHECK (media_type IN ('image/jpeg','image/png','image/webp','image/gif'))
);
