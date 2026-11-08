-- Refuses to drop rows that users.granted_repositories never received: no backfill was written.
do $$
begin
  if exists (select from public.private_repositories) then
    raise exception 'private_repositories still holds rows; move them into users.granted_repositories first';
  end if;
end
$$;

drop table public.private_repositories;
