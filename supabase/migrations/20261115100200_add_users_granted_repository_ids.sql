-- Opaque ids of the private repositories a profile was scanned from, so revoking one deletes it.
alter table public.users
  add column granted_repository_ids bigint[] not null,
  add constraint users_granted_repository_ids_are_positive check (0 < all(granted_repository_ids));
