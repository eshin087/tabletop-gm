"""The host console: a local browser console for running an approved exercise.

  session   the approved pack plus its append-only decision log (no other state)
  conduct   a deterministic check of anything the AI co-host writes
  cohost    the optional AI co-host (needs the ``anthropic`` package and a key)
  server    a standard-library HTTP server bound to localhost
  console   the single self-contained page, also written by ``ttx build`` as host.html

The engine still owns the script, the clock, the log, and the score. The
co-host suggests; the host confirms; ``ttx.decision_log`` records.
"""
