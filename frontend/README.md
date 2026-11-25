# EMR frontend

The React and TypeScript application contains the clinical workspace, patient portal and shared authentication flow. Both execution modes use the same components and request interface.

## Development

Use the Node.js 22 release family used in CI. Install dependencies from the lockfile:

```bash
npm ci
npm run dev
```

Start the API separately using the [root setup instructions](../README.md#run-locally). The default API origin is `http://127.0.0.1:8000`; Vite serves the interface at `http://localhost:5173` by default.

## Build modes

| Mode | Command | API transport |
| --- | --- | --- |
| Local / hosted API | `npm run build` | HTTP to `VITE_API_BASE_URL`, or the local default |
| Same-origin API | `VITE_API_BASE_URL='' npm run build` | HTTP relative to the frontend origin |
| Isolated browser workspace | `VITE_EMR_BROWSER=1 npm run build` | Worker messages to the packaged Python runtime |

For browser mode, first run `python scripts/build_browser_runtime.py` from the repository root. The public runtime is placed under `frontend/public/runtime/` and excluded from source control. Do not place real credentials in `VITE_` variables; the frontend bundle is public.

Serve a built application locally with `npm run preview`. GitHub Pages builds the browser mode using a relative base path and publishes the resulting `dist/` directory.

## Source organization

- `src/App.tsx` owns staff navigation, selected chart and authenticated account state.
- `src/components/` contains the staff dashboard, patient charts, worklists, portal, sign-in and original SVG artwork.
- `src/api.ts` is the request boundary; `src/browserApi.ts` bridges browser-only requests to the worker.
- `public/runtime-worker.mjs` initializes the browser backend and serializes requests.
- `src/ClinicalWorkspace.css` defines shared visual tokens, clinical and patient treatments and responsive layouts. Component styles remain close to their respective views.
- `src/types.ts` describes API response and input contracts. Pure helpers cover date formatting, clinical snapshots and record grouping.
- `tests/` covers frontend business rules; the root `scripts/` directory contains Chromium workflow checks.

## Checks

```bash
npm run lint
npm test
npm run build
```

The [CI workflow](../.github/workflows/checks.yml) also builds and exercises the browser-only and PostgreSQL-backed applications. UI changes should retain labeled controls, focus visibility, loading/error states and clear clinical status text. Keep patient-facing language readable; do not rely on color alone to communicate status.

See [design decisions](../docs/UX_DESIGN.md) and [the release audit](../docs/UX_AUDIT.md). The application is for fictional patient records only.

## Capture reference screenshots

The browser smoke test can save actual application screenshots to a separate output directory. It runs only against the locally served browser build and uses the fictional starting records. Prepare the browser-mode build using the root README, then run these commands from the repository root in a disposable environment:

```bash
python -m pip install playwright==1.51.0
python -m playwright install chromium
mkdir -p /tmp/emr-pages
ln -s "$PWD/frontend/dist" /tmp/emr-pages/primary-care-emr
python -m http.server 4174 --bind 127.0.0.1 --directory /tmp/emr-pages
```

In another terminal, from the repository root with the same Python environment active:

```bash
EMR_SCREENSHOT_DIR=/tmp/emr-screenshots python scripts/check_browser_emr.py
```

The test saves staff and patient sign-in, dashboard, chart, and desktop/mobile patient home captures. Stop the temporary HTTP server when finished. Use a fresh temporary serving directory (or remove the previous symlink) before repeating the setup.

Successful Checks runs upload these PNGs as the `emr-workspace-screenshots` artifact for 30 days. The images are not shipped with the application and require no additional frontend asset requests. They record the tested build rather than an independent inspection of the public site.
