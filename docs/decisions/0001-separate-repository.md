# ADR 0001: keep the Home Assistant integration in a separate repository

## Status

Accepted for the prototype.

## Context

The Octi ecosystem contains an Android client, a browser client and a server. Home Assistant has its own packaging, lifecycle, test and review conventions. Putting a Python integration in the web client repository would couple unrelated release cycles and would not match HACS's expected repository layout.

The Octi maintainer explicitly recommended a separate community repository and offered to link it from the ecosystem documentation after a working prototype passes interop tests.

## Decision

Build the Home Assistant integration as a standalone public repository distributed through HACS. Keep protocol questions and compatibility changes visible in the main `d4rken-org/octi` repository; keep Home Assistant implementation and release work here.

## Consequences

Positive:

- independent Home Assistant releases and issue tracker;
- native HACS layout and validation;
- smaller review surface for Octi maintainers;
- a clear place for HA-specific security and entity decisions.

Costs:

- one more repository to maintain;
- protocol changes must be tracked explicitly;
- the integration needs pinned upstream fixtures and compatibility tests.

## Revisit when

Revisit only if Octi later adopts an official multi-client SDK or explicitly decides to own a first-party Home Assistant integration.
