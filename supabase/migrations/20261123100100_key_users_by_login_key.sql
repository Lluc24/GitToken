-- login keeps GitHub's casing; login_key is the case-insensitive identity lookups match on.
alter table public.users
  drop constraint users_login_check,
  drop constraint users_login_key,
  add column login_key text not null generated always as (lower(login)) stored,
  add constraint users_login_key_unique unique (login_key);
