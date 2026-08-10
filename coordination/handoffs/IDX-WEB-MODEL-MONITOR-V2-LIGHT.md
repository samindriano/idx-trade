# Handoff

from: ChatGPT ARCHITECT
to: LOCAL / Codex
task_id: IDX-WEB-MODEL-MONITOR-V2-LIGHT
model_used: GPT-5.6 Sol
reasoning_level: architect/review
source_repository: `samindriano/idx-trade`
branch: `frontend/model-monitoring-v1`
scope: Replace the first dark/sidebar-heavy model-observatory UI with a simpler light single-page finance dashboard while preserving frozen model facts and the forward-outcome access boundary.

files_changed:
- `apps/web/app/page.tsx`
- `apps/web/app/globals.css`
- `docs/checkpoints/2026-08-10_WEB_MODEL_MONITOR_V2_LIGHT_REDESIGN.md`
- `coordination/handoffs/IDX-WEB-MODEL-MONITOR-V2-LIGHT.md`

findings:
- The prior UI was information-dense but visually read as a generic dark developer/admin dashboard.
- The user explicitly prefers a bright interface and a simpler single page containing only monitoring essentials.
- The model-switching data structure remains useful and was retained.
- No external chart or animation package is necessary for this iteration; SVG + CSS transitions provide the required interaction with less dependency surface.

decisions_made:
- Remove the fixed left sidebar.
- Use light top navigation.
- Keep only model selector, four core historical metrics, one fold chart, one forward-test panel, and one model-comparison table.
- Hide V3 backlog entries inside the model selector as disabled future models rather than displaying a dedicated research panel.
- Keep HGB_XS_MARKET's forward contract visually distinct from historical-only candidates.
- Preserve no-outcome-rendering behavior.

blocking_risks:
- This GitHub-side redesign has not yet been built in the user's local Next.js runtime.
- Existing npm audit warnings are outside this visual task and were not modified.

validation_run:
- Not run by ChatGPT connector after redesign.
- Prior scaffold verification before redesign: Next production build + TypeScript + static generation passed and HTTP smoke test returned 200 OK.

recommended_next_action:
1. Pull `frontend/model-monitoring-v1` into the existing web worktree.
2. Run `npm run build` in `apps/web`.
3. Start dev server and inspect at desktop width.
4. Fix only build/type/layout regressions; do not alter model semantics or access fresh-forward outcomes.
5. Return a full-page screenshot for the next visual review.
