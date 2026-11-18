-- The case-insensitive identity of a login, which lookups match on.
alter table public.users
  add column login_key text not null generated always as (lower(login)) stored,
  add constraint users_login_key_unique unique (login_key);
