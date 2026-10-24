# Maintainer Pull Request Review Checklist

Use this checklist when reviewing pull requests for Critique. Apply the checks relevant to the changes in the PR, and record any issues that need to be addressed before merging. This checklist supports review; it does not guarantee approval or a merge.
## 1. Tests

- [ ] Check that appropriate tests cover the changed behaviour.
- [ ] Check that relevant existing tests still pass.
- [ ] Verify that new behaviour and important edge cases are tested.
- [ ] Record which checks were run and any failures or limitations.

## 2. Analytics

- [ ] If a new analytics event is introduced, verify that it is added to both analytics allowlists.
- [ ] Check that event names are consistent between event tracking and the analytics dashboard.
- [ ] Verify that relevant analytics validation and dashboard behaviour are tested.

## 3. Security and Caching

- [ ] Check that security-related HTTP headers are asserted in tests where applicable.
- [ ] Check that cache-control headers and caching behaviour are tested where applicable.
- [ ] Verify that changes do not unintentionally weaken existing security or caching protections.

## 4. Database Migrations

- [ ] Check that schema changes use additive, backward-compatible migrations where appropriate.
- [ ] Verify that migrations work with both SQLite and PostgreSQL.
- [ ] Consider existing data and installations when reviewing schema changes.
- [ ] Check that migration and rollback behaviour is tested where supported.

## 5. Dependencies

- [ ] Review whether each new dependency is necessary for the change.
- [ ] Check whether existing project functionality can meet the requirement without adding a dependency.
- [ ] Consider the dependency's maintenance status, compatibility, and security implications.
- [ ] Confirm that dependency changes are documented and configured appropriately.