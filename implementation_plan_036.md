# Implementation Plan — Sirius-CLI v0.3.6: Error UX & Empty State Handling

This plan outlines the design and step-by-step changes to implement the features requested for the `v0.3.6` release: empty state handling inside `SiriusTable`, toast notifications on successful CRUD operations, graceful 404 handling on deleted FK navigation, and table loading skeleton/overlay states.

## User Review Required

> [!IMPORTANT]
> The development cycle requires creating a GitHub issue, branching to a feature branch, writing code and running dual environment tests, opening a PR, obtaining user approval, merging/squashing, and tagging the release.
> We will create the issue and branch immediately upon approval of this plan.

## Proposed Changes

### Component 1: Git Issue & Branch Setup

- Create a GitHub issue using `gh` CLI in WSL for the v0.3.6 features.
- Create and check out a new local branch: `feature/error-ux-empty-states`.

---

### Component 2: Frontend UI Templates

#### [NEW] [SiriusToast.tsx.jinja2](file:///c:/Users/HYPER/Desktop/bcg-prep/sirius_cli/templates/frontend/src/components/SiriusToast.tsx.jinja2)
- Create a reusable, self-dismissing toast notification component:
  - Props: `message: string`, `type: 'success' | 'error'`, `onClose: () => void`, `duration?: number` (defaults to 3000ms).
  - Uses `lucide-react` icons (`CheckCircle2` for success, `AlertCircle` for errors, `X` for manual dismiss).
  - High-premium glassmorphism styles: semi-transparent dark background, borders, slide-in animations.

#### [MODIFY] [index.css.jinja2](file:///c:/Users/HYPER/Desktop/bcg-prep/sirius_cli/templates/frontend/src/index.css.jinja2)
- Add keyframes and styles for `@keyframes slide-in` and `.animate-slide-in` to animate the toast popup.

#### [MODIFY] [SiriusTable.tsx.jinja2](file:///c:/Users/HYPER/Desktop/bcg-prep/sirius_cli/templates/frontend/src/components/SiriusTable.tsx.jinja2)
- Update `SiriusTableProps` to accept:
  - `loading?: boolean`
  - `onAdd?: () => void` (CTA callback)
- In the table `tbody`:
  - If `loading` is true and `records.length === 0` (initial load), render 5 skeleton rows with pulsing grey block placeholders (`h-3.5 bg-slate-800 rounded animate-pulse`).
  - If `loading` is false and `records.length === 0` (empty state), render a single full-width cell spanning all columns:
    - Beautiful inbox/database empty-state icon.
    - Title: "No records found".
    - Description: "Get started by creating a new record in this table."
    - CTA button: "Add Record" invoking `onAdd`.

#### [MODIFY] [TableCrud.tsx.jinja2](file:///c:/Users/HYPER/Desktop/bcg-prep/sirius_cli/templates/frontend/src/TableCrud.tsx.jinja2)
- Import `SiriusToast` and manage a local `toast` state:
  ```tsx
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  ```
- Replace standard `alert()` calls on save/delete success with toast notifications.
- In `handleSubmit` (Create/Update) and `handleDelete` (Delete):
  - On success: show success toast (e.g. "Record saved successfully", "Record deleted successfully").
  - On error: show error toast.
- In `useEffect` for handling the `highlight` URL parameter:
  - Fetch `/api/{table}/{highlight_id}` directly.
  - If the fetch returns a `404`, trigger an error toast: "Record not found (it may have been deleted)".
- Update JSX:
  - Pass `loading={loading}` and `onAdd={openCreateModal}` to `<SiriusTable />`.
  - When `loading` is true and we already have records (`displayedRecords.length > 0`), show a semi-transparent absolute overlay over the table card with a spinner and "Updating..." status text.
  - Render `<SiriusToast ... />` if the toast state is active.
  - Remove the old `{displayedRecords.length === 0 ? (...) : (...) }` code wrapper since `SiriusTable` handles empty/skeleton states internally.

---

### Component 3: Version Bump Synchronization

Modify the version string to `0.3.6` in the following files:
- [pyproject.toml](file:///c:/Users/HYPER/Desktop/bcg-prep/pyproject.toml)
- [docs/index.html](file:///c:/Users/HYPER/Desktop/bcg-prep/docs/index.html)
- [CHANGELOG.md](file:///c:/Users/HYPER/Desktop/bcg-prep/CHANGELOG.md) (Log changes under `## [0.3.6]`)
- [AUDIT.md](file:///c:/Users/HYPER/Desktop/bcg-prep/AUDIT.md) (Update title and current state table)

---

## Verification Plan

### Automated Tests
- Run `wsl python3 -m pytest tests/` in WSL.
- Run `python -m pytest tests/` in Windows PowerShell.

### Manual Verification
- We can generate a temporary preview project using `python -m sirius_cli.cli preview` or run tests generating scaffolds to verify all files are generated without syntax errors.
