-- Saved profiles predate daily activity; expiring them makes the next lookup rescan instead of
-- drawing an empty heatmap. They leave the leaderboard until then.
update public.users set fetched_at = '-infinity';
