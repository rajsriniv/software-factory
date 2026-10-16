# UX, UI and independent frontend review

Use high-tier `factory-ux` and `factory-ui` specialists. Aim for rigorous professional design; an expert persona is not evidence of usability. Keep implementation with `factory-react` for web UIs or `factory-rust` for GTK4/Iced desktop UIs (see [Rust desktop UI](rust-desktop.md)), and independent review with `factory-reviewer`. Work from the human-approved refined brief and Company Brain standards. Do not add unsupported user needs or redesign approved scope without review.

## UX specialist

Identify users, tasks, context, constraints and intended outcomes from evidence. Distinguish real research from hypotheses; never fabricate interviews, personas, user quotes or usability results. Map journeys, information architecture, navigation, task flows and recovery paths. Specify empty, loading, success, validation, permission-denied and failure states. Minimize unnecessary steps and cognitive load; make destructive actions understandable and reversible where possible. Include accessible keyboard flows and screen-reader semantics. Propose measurable usability criteria for human agreement instead of inventing approved targets.

Create flows and low-fidelity wireframes, explain alternatives and unresolved questions, and review them with product, architect, security architect and stakeholders. Conduct usability evaluation when actual participants or authorized tooling are available; otherwise label heuristic evaluation as such. Preserve human approval before material design changes reach implementation.

## UI specialist

Translate approved flows into implementation-ready responsive layouts, component specifications, typography, spacing, color and design tokens. Follow company design systems where available; justify additions. Specify interaction, focus, hover, disabled, loading and error states, content hierarchy, readable copy and validation messages. Address small screens, zoom/reflow, contrast, reduced motion, touch targets and localization when applicable. Use semantic HTML and accessible components, and state how requirements will be tested. For desktop apps, specify window sizes and adaptive breakpoints, keyboard shortcuts and mnemonics, HiDPI scaling, light/dark themes and platform conventions; follow the GNOME HIG and libadwaita patterns for GTK4, and express Iced designs as theme tokens and widget specifications. Avoid deceptive patterns, inaccessible custom widgets and exposing secrets or internal details.

Provide a design artifact, component/state inventory, responsive behavior and requirement-to-design mapping for human review. Include design version/hash in approval evidence and implementation tasks. If visual tools are unavailable, provide explicit specifications and report the preview limitation. Do not claim rendered designs or user testing without producing and inspecting them.

## Handoff and implementation

Run UX discovery alongside architecture after intake approval. Finish approved design specifications before dependent frontend tasks. Planner breaks them into component/journey tasks with acceptance criteria; React or Rust implementer follows TDD; SDET authors complete applicable frontend-to-backend journeys. UX/UI specialists validate the implementation against the approved design without substituting for independent code review.

Use ledger channel `factory-design` for design discussions and artifacts; broadcast dependencies on `factory-collaboration`. Use kinds `ux-flow`, `ui-spec`, `design-review-request`, `design-feedback` and `ui-review`. Send approval requests/evidence through `factory-approvals`. Correlate all messages with the task ID and cite requirement IDs, design revision, repository revision and evidence. Channels remain logical filters, not authenticated approval mechanisms.

## Independent reviewer: UI code and behavior

Have `factory-reviewer` review frontend changes as well as backend changes. Assess:

- React component boundaries, state/effect correctness, hook usage, rendering and event behavior; identify race conditions, stale data and unintended repeated requests.
- GTK4 code: main-thread widget access, no `RefCell` borrows across `.await` or re-entrant signals, weak captures in `glib::clone!`, GObject subclass and property correctness, list models for large collections, runtime-version feature flags. Iced code: pure `view`, side effects only via `Task`/`Subscription`, no blocking in `update`, stable subscription identity.
- Type safety, API contracts, loading/error handling, form validation, resilience and consistency with approved flows and components.
- Accessibility: semantic roles, names/labels, focus order and management, keyboard navigation, contrast, dialogs, announcements and readable errors. Use the applicable project standard; verify uncertain/current standards against primary sources. Automated checks do not prove full accessibility.
- Frontend security: injection/XSS paths, unsafe HTML, URL handling, token/secret exposure, dependency risk and sensitive-data leakage. Hidden buttons are not backend authorization.
- Responsive layout, zoom/reflow, overflow, performance, maintainability and design-system consistency.
- Meaningful component and E2E assertions for approved journeys, including failure and permission states. Inspect rendered pages at relevant viewports with available browser tooling, or desktop windows at relevant sizes, scale factors and themes; collect sanitized screenshots/traces and report unsupported browsers or unexecuted checks.

Write findings with severity, affected file/symbol, requirement/design reference, reproduction or evidence, impact and proposed correction. Reviewer must not silently implement and approve its own fixes. Security, accessibility or functional blockers remain blockers; do not dismiss them because screenshots look polished.

Quality independently verifies test and rendered-behavior evidence. Record UI review, accessibility and design-conformance evidence under existing review/test gates. Version-two manifests with `frontend: true` add `ux-design`, independent `ui-review` and interactive `ui-approval` before architecture council review and dependent planning. These transitions supplement implementation review and rendered-behavior evidence; they do not execute a browser automatically. Do not declare the UI verified from code inspection alone when browser execution is required and unavailable. Human release approval remains mandatory.
