create table if not exists verifies (
  discord_id text primary key,
  roblox_id text not null,
  roblox_name text not null,
  updated_at timestamptz not null default now()
);

alter table verifies
add column if not exists roblox_display_name text;

create index if not exists verifies_roblox_id_idx on verifies (roblox_id);

create table if not exists pending_game_verifies (
  discord_id text primary key,
  discord_name text,
  roblox_id text not null,
  roblox_name text not null,
  roblox_display_name text,
  code text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create unique index if not exists pending_game_verifies_code_idx on pending_game_verifies (code);
create index if not exists pending_game_verifies_roblox_id_idx on pending_game_verifies (roblox_id);
create index if not exists pending_game_verifies_expires_at_idx on pending_game_verifies (expires_at);
