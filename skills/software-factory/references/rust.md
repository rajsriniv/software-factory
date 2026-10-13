# Rust profile

Use for Rust services, CLIs, libraries and the core of Rust desktop apps. For GTK4 or Iced user interfaces, also read [Rust desktop UI](rust-desktop.md). Verify crate APIs against the pinned versions' docs.rs pages and changelogs; Rust ecosystem APIs change between minor versions and remembered signatures are not evidence.

## Toolchain and build

Pin the toolchain in `rust-toolchain.toml` (channel, `rustfmt`, `clippy`, required targets) and declare `edition` and `rust-version` (MSRV) in `Cargo.toml`. Commit `Cargo.lock` for binaries and applications, and build with `--locked` in CI. Use a workspace with `[workspace.dependencies]` and `[workspace.lints]` so versions and lints stay consistent across crates. Treat `build.rs` and procedural macros as code executed at build time; review them like any other code and justify new ones.

Required checks, each recorded with command, revision and result:

- `cargo fmt --all --check`
- `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`
- `cargo test --workspace --all-features --locked` (or `cargo nextest run` plus `cargo test --doc`, because nextest skips doctests)
- Feature combinations with `cargo hack --each-feature` or `--feature-powerset` when crates expose features; `--no-default-features` builds where supported
- MSRV build on the declared `rust-version`
- `cargo deny check` (advisories, licenses, bans, sources) and/or `cargo audit`; unknown registries and git dependencies need justification
- Coverage with `cargo llvm-cov`; public library API compatibility with `cargo semver-checks`
- `cargo doc --no-deps` with `RUSTDOCFLAGS="-D warnings"` for libraries
- SBOM (`cargo cyclonedx` or `cargo auditable` builds) and container or package build

## Code standards

- Default to `#![forbid(unsafe_code)]`. Any `unsafe` needs a documented invariant in a `// SAFETY:` comment, a minimal scope, tests that exercise it, and Miri (`cargo +nightly miri test`) where the code is Miri-compatible. FFI boundaries need ownership, lifetime, nullability and thread-safety contracts written down.
- Libraries return typed errors (`thiserror` or hand-written enums). Binaries may aggregate with `anyhow` or `eyre` and add context at boundaries. No `unwrap`, `expect` or `panic!` on input-dependent paths outside tests; consider the `clippy::unwrap_used` and `clippy::expect_used` lints. Do not use panics for control flow, and decide `panic = "abort"` vs unwind explicitly.
- Model invariants in types: newtypes for IDs and units, enums instead of boolean flags or stringly typed states, `#[non_exhaustive]` on public enums and structs that may grow. Avoid needless `clone`, `Rc<RefCell<_>>` and `Arc<Mutex<_>>` when ownership or message passing fits.
- Validate at trust boundaries. Use `serde` with `#[serde(deny_unknown_fields)]` where strictness is a requirement, bound input sizes, and avoid unbounded recursion on untrusted data. Use `secrecy` or zeroizing types for secrets and keep them out of `Debug` output and logs.
- Keep integer overflow behavior explicit (`checked_`, `saturating_` or `wrapping_` operations) on input-derived arithmetic; release builds wrap silently.

## Async and concurrency

Pin one async runtime (normally Tokio) and its features. Never block the executor: use `spawn_blocking` or a dedicated thread for blocking I/O and CPU-heavy work. Do not hold `std::sync::Mutex` or `RefCell` borrows across `.await`. Check cancellation safety of every branch in `tokio::select!`. Implement graceful shutdown with cancellation tokens and bounded drain time; join or explicitly detach spawned tasks. Use bounded channels for backpressure. Test concurrency-sensitive code with `loom` or deterministic interleavings where feasible; a passing ordinary test does not prove absence of races.

## Testing

Unit tests sit beside code; integration tests in `tests/` exercise the public API only. Use property tests (`proptest`) for parsers, codecs and invariants, `insta` snapshots only with reviewed snapshot changes, and fuzzing (`cargo fuzz`) for untrusted-input parsers when risk warrants it. A compile error is not valid RED evidence; write the test against an existing signature that returns the wrong result, or stub the item with `todo!()` and record the resulting test panic as RED.

## Services and observability

Use `tracing` with structured fields and request correlation; export through OpenTelemetry when the architecture requires it. Never log secrets or personal data. Expose health and readiness endpoints for services. For containers, build with cached dependencies (for example `cargo-chef`), run as non-root on a minimal or distroless base, and pin base image digests. Release builds should set `--remap-path-prefix` or equivalent to avoid leaking build paths.

Implementers edit only assigned crates and paths and cannot change acceptance criteria, lints, `deny.toml` policy or MSRV without planner and reviewer agreement.
