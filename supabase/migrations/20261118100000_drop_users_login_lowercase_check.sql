-- login may keep GitHub's casing; the case-insensitive identity moves to login_key.
alter table public.users drop constraint users_login_check;
