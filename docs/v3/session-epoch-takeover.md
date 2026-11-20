# Session-bound takeover contract

`nx_takeover` accepts an optional `expected_session_epoch` in canonical
`<positive PID>:<positive UTC start ticks>` form, with the PID equal to
`expected_pid`. The tick value is the .NET `DateTime` UTC tick count used by
the existing bridge session identity. Callers must obtain it from current
process evidence; a historical session value is not a current credential.

When present, the host sends only the distinct wire command
`ownership.takeover_if_session` with the epoch as a required field. A bridge
without this command returns `UNKNOWN_COMMAND`; the host must not retry using
`ownership.takeover`. The bridge compares the supplied PID and process epoch
with its own startup-captured process-only metadata under its lifecycle lock,
before changing ownership state, incrementing the binding epoch, queuing work,
or calling the model adapter. A mismatch is `SESSION_MISMATCH` and missing or
malformed fields are `INVALID_REQUEST`. Existing UNKNOWN and stop guards apply.

The legacy request with no epoch continues to use `ownership.takeover`; it does
not gain a session-generation guarantee. A successful strict takeover returns
the matching `session_epoch`. The caller must still verify the response,
ownership, current binding, selected part, and clean-return evidence. This
contract does not authorize model work, revive earlier ownership credentials,
or change the freeze and manual-recovery rules.
