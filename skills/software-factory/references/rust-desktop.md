# Rust desktop UI profile: GTK4 and Iced

Read [Rust](rust.md) first; every Rust check applies. Verify widget, macro and builder APIs against the pinned crate versions. GTK4 bindings and Iced both change APIs between releases, and Iced in particular renames core types between minor versions.

## Choosing a toolkit

Toolkit choice is an architecture decision recorded in an ADR, not an implementer choice. Compare against the approved requirements:

- **GTK4 (`gtk4-rs`, usually with `libadwaita`)**: native GNOME/Linux look and behavior, mature AT-SPI accessibility, platform integration (portals, GSettings, notifications, file choosers). Windows and macOS builds are possible but need bundled GTK runtimes and look non-native.
- **Iced**: pure-Rust, cross-platform, Elm-style architecture, GPU (`wgpu`) rendering with a software (`tiny-skia`) fallback. Accessibility and platform integration are less mature. Before approval, verify the pinned Iced release's screen-reader, IME and keyboard-navigation support from its changelog and issues, and record gaps as explicit risks for UX, security architecture and the human approver. Do not choose Iced for a product with screen-reader requirements until support is demonstrated.

## GTK4

- Pin `gtk4`, `glib`, `gio` and `libadwaita` crates together, and enable only the `v4_*` / `v1_*` feature flags that match the minimum runtime version the product supports. Using a newer feature than the target runtime ships is a defect.
- GTK is single-threaded. Touch widgets only on the main thread. Run async UI work with `glib::spawn_future_local`; move blocking or CPU-heavy work to threads or a separate Tokio runtime, and return results through `async-channel` or `glib` channels. Never call `block_on` on the main loop.
- Do not hold `RefCell` borrows across `.await` or across calls that can re-enter signal handlers; that panics at runtime. Capture widgets in closures with `glib::clone!` and weak references to avoid reference cycles and leaks; handle the upgrade-failed case.
- Structure custom widgets as GObject subclasses with an `imp` module, `#[derive(Properties)]` for properties and `#[derive(CompositeTemplate)]` with `.ui` or Blueprint templates compiled into GResources. Keep business logic in plain Rust types that are testable without GTK.
- Use actions (`gio::SimpleAction`, `gtk::Application::set_accels_for_action`) for commands so menus, shortcuts and buttons share one path. Persist preferences through GSettings with a schema validated by `glib-compile-schemas --strict`.
- Use `gtk::ListView`/`GridView`/`ColumnView` with `GListModel` and factories for large or dynamic collections; `ListBox` is for small, static sets.
- Follow the GNOME Human Interface Guidelines when using libadwaita: `AdwApplicationWindow`, header bars, `AdwToastOverlay`, `AdwAlertDialog` for destructive confirmation, and `AdwBreakpoint` for adaptive layouts at narrow widths.
- Accessibility: give every interactive widget an accessible name (visible label, `mnemonic-widget`, or `update_property` with `gtk::accessible::Property::Label`), correct `AccessibleRole` on custom widgets, logical focus order and full keyboard operation. Verify with Orca and the GTK inspector (`GTK_DEBUG=interactive`) or Accerciser.
- Internationalize with `gettext` (`gettext-rs`), never concatenate translatable fragments, and test right-to-left layout when localization is in scope.
- Distribute through Flatpak when targeting Linux desktops: pin the GNOME runtime, keep `finish-args` minimal, and use portals instead of broad `--filesystem` or session-bus access. Validate with `desktop-file-validate`, `appstreamcli validate` and `flatpak-builder --lint` where available; Flatpak builds need vendored or `flatpak-cargo-generator` sources because the build sandbox is offline.

## Iced

- Pin the exact `iced` version and features (renderer, `tokio`, `image`, `svg`, `advanced`). Check the changelog before using any API you remember; for example, `Command` became `Task` and the `Application`/`Sandbox` traits gave way to the `iced::application` builder in 0.13.
- Follow the Elm architecture strictly: state is owned by the app struct, `view` is a pure function of state, `update` handles one `Message` and returns a `Task` for side effects. Do not perform I/O, sleep or block inside `update` or `view`. Use `Subscription` for timers, sockets, file watchers and other event streams, keyed so they are not restarted every frame.
- Keep `Message` an enum that is cheap to clone; carry results as `Result<T, ErrorType>` with errors converted to user-visible state. Split large apps into screens or components, each with its own `State`, `Message`, `update` and `view`, mapped into the parent with `Element::map` and `Task::map`.
- Keep `view` cheap: avoid allocation-heavy recomputation, use `lazy` or cached data for expensive subtrees, and `Scrollable` with virtualization strategies for long lists.
- Define a custom `Theme`/palette as design tokens from the approved UI specification, and check contrast in both light and dark variants.
- Test both GPU and software rendering paths when the product must run without a GPU or in VMs. Record the graphics backend in E2E evidence.
- Distribute per platform: signed and notarized macOS bundles, signed Windows installers, and Flatpak or AppImage on Linux. Code-signing keys stay in release tooling, never in the repository or CI logs.

## Testing desktop UIs

- Put the bulk of tests on logic without a display: Iced `update` functions (feed messages, assert state and returned tasks) and GTK-independent view models and services.
- GTK widget tests need GTK initialised on the test's main thread. Use the `#[gtk::test]` attribute where the pinned `gtk4` crate provides it, otherwise a single-threaded harness. Run them headless under Xvfb (`xvfb-run`) or a headless Wayland compositor in CI, and record which.
- Iced UI tests: use the `iced_test` simulator if the pinned version provides it; otherwise test through `update`/`view` structure and screenshot comparison with reviewed baselines.
- End-to-end desktop journeys for GTK apps can drive the real application through AT-SPI (for example Dogtail or similar tooling); accessible names double as stable locators, so missing names are both an accessibility and a testability defect. Iced apps with limited AT-SPI exposure need a documented alternative such as simulator-driven journeys plus manual exploratory evidence, independently reviewed per [TDD and SDET](tdd-sdet.md).
- Capture sanitized screenshots, logs and the display backend, scale factor, theme and locale used. Test at 100% and 200% scaling and with a narrow window when adaptive layout is in scope.

## Release artifacts

Desktop releases ship packages, not container images. The immutable artifact for human approval is the exact Flatpak bundle/OCI ref, AppImage, MSI or notarized bundle digest, with SBOM and signature. The AWS stages apply only to backend services or update/distribution infrastructure that the architecture includes.
