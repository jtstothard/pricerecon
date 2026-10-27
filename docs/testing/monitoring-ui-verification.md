# Ticket 01 post-fix rendered browser verification

2026-10-27. Tested implementation HEAD 534cecaece62e30f50c680b40af5b4c7f561b6e4,
branch t3/preserve-watch-edit-intent, against its built frontend. Integration merger
is separately checking the merged source. This is agent-observed regression proof,
not buyer usability acceptance of the future discovery workflow.

Guarded fixture: `/Users/jay/.scratch/watch-category-discovery-implementation/monitoring_ui_server.py`; MonitoringHarness temporary SQLite,
cleared environment, controlled connector registry/results and captured notification
sends, paused scheduler, explicit manual checks. Seed LEGACY and disabled copy.
App served only at 127.0.0.1:8876. Browser isolated session with empty config and
existing installed Google Chrome; no installs, accounts, merchant navigation or
production DB operations. T3 preview's two prior snapshot timeouts justified fallback.

Expected and observed:
- Active and paused saved searches rendered; normal edit/check/detail controls exist.
- Saved interval30m rendered as Every30m(saved), with select value30m.
- Changed only Display title to Offline browser edited title and saved through UI.
- API readback compared name/query/category/sources/filters/schedule/notifications/
  grouping/enabled/synonym_groups/source_queries with the pre-edit API record:
  unexpected_changes=[], pass=true. Saved title matched the edit.
- Reloaded dashboard, clicked manual Check, opened actual saved-search detail.
  One Militado ML05B blue listing rendered at GBP90.00, with retained30m schedule.
  No events/price history were fabricated by the unchanged check.
- After reload/check, API reconfirmed title, Europe/London timezone/timewindow,
  all three notification channels with price_drop only, structured parts exclusion,
  and disabled not-a-real-source. All checks returnedtrue.
- Browser errors output empty. Screenshot `/Users/jay/.scratch/watch-category-discovery-implementation/monitoring-ui-green.png` retained outside the repo and visually inspected.

Browser session closed; local server stopped after verification. Offline fixture
proof does not accept live sources or the later buyer discovery walkthrough.
