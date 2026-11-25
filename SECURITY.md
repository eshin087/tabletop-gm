# Security

## Outbound calls

The `ttx` engine makes no network calls unless you ask for one of the three below. Building, validating, scoring, and reporting are fully offline. There is no telemetry.

| Call | When | Destination | What is sent | What changes |
|---|---|---|---|---|
| Tenable Vulnerability Management / Tenable One API | Only `ttx seed --mode tenable` | `https://cloud.tenable.com` (`/vulns/export`, `/assets/export` and their status and chunk endpoints), or the same endpoints through pytenable when it is installed | Your API keys in the `X-ApiKeys` header; export filters (severity critical and high, state open and reopened) | Nothing in your data. The export endpoints create temporary export jobs that Tenable expires. No scan, asset, finding, tag, or setting is created, changed, or deleted. Read-only keys are enough. |
| Anthropic API | Only `ttx host`, only when `ANTHROPIC_API_KEY` is set and the optional `anthropic` package is installed, and only when the host presents an inject, pushes the room, or presses Enter on a decision | `https://api.anthropic.com` through the official SDK | Your API key in the request header. The exercise frame (organization name and description, role names, notify parties, the three attack path assets with their finding IDs and CVEs, the ground rules). The current inject's text. For a suggestion, that inject's expected actions. The decisions already logged, and the sentence the host just typed. Later injects are never sent. | Nothing on your systems. The answer is shown to the host and is not logged until the host clicks. `ttx host --no-ai` or `TTX_HOST_AI=off` turns it off. |
| CISA Known Exploited Vulnerabilities feed | Only `ttx seed --kev-check` | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` | One unauthenticated GET with a `Tabletop-GM/<version>` user agent | Nothing. Use `--kev-file` with a local copy to stay offline. |

The launchers (`start-windows.bat`, `start-mac.command`, `start-linux.sh`) make these calls on the first run only:

| Call | When | What changes |
|---|---|---|
| PyPI (`pip install`) | First run, through `scripts/bootstrap.py` | Downloads the pure-Python dependencies into a private `.venv` folder inside the download. Nothing is installed system-wide. |
| winget (Windows) or Homebrew (macOS) | Only when Python 3.11+ is missing and you answer yes at the prompt | Installs Python 3.12 for your user account from the official package. |
| Browser opens python.org | Only when Python is missing and cannot be installed automatically | Nothing; you install Python yourself. |

The launcher never installs Claude Code. When Claude Code is missing it prints the official install commands for you to run.

`.claude/settings.json` pre-approves only these commands in Claude Code, so they run without a permission prompt:

- the `ttx` engine from the project's own `.venv`
- `scripts/bootstrap.py`
- file edits under `out/`

Every other command and edit still asks. Claude Code lists these rules in its trust prompt before applying them.

The guided workflow runs inside Claude Code, which has its own outbound traffic:

| Call | When | What is sent |
|---|---|---|
| Anthropic, through Claude Code | Whenever you use `/tabletop` | Your chat messages and the files Claude reads. That includes the intake, the seed, clock output, and the text of any plan documents during policy ingest. It is governed by your Claude Code account terms. The `ttx` CLI itself never calls Anthropic. |
| Web research, through Claude Code's web tools | Only when you run the `pack_research` or `incident_research` skill | Search queries about the sector's regulations or public incidents. No organization data is needed or sent. |

Live mode (`ttx log`, the `facilitate` skill) adds no outbound calls. The decision log is a local JSON file under `out/live/`, and its export, score, and report run offline like every other `ttx` command. The chat itself still goes through Claude Code as above.

`ANTHROPIC_API_KEY` in `.env` is read only by `ttx host`, for its optional AI co-host. No other command reads it. The key is never written to the log, the reports, or the console page.

## The host console

`ttx host` starts a small web server from the Python standard library. It serves two pages to your browser: the host console at `/`, which is private to the host, and the room screen at `/room`, which goes on the wall or the projector.

- It binds to `127.0.0.1` only. It is not reachable from another computer.
- It refuses any request whose Host header is not `127.0.0.1` or `localhost` on its own port.
- Every call that reads the full exercise or changes anything must carry a random token created for that run and embedded in the host console page. Another page open in the same browser cannot drive the console.
- The room screen and its data (`/room` and `/room/state`) need no token, so the screen can open in a second window. They are read-only and carry only what the room is meant to see: no expected answers, no plan quotes, no clock table, no inject that has not been presented. The two rules above still limit them to this computer.
- It sends no CORS headers, and the page loads nothing from the network: no fonts, no scripts, no analytics.
- Each click is one append to `decision_log.json` through the same code as `ttx log`.
- `ttx host --replay` opens a copy of a recorded log read-only. The original file is never written.

The standalone `host.html` from `ttx build` makes no network request at all. It keeps the session in that browser's local storage, under a key derived from the exercise's approval hash, until you export `decision_log.json`. Clear the browser's site data to remove it. The page contains the full approved exercise, including the expected answers, so treat the file like the facilitator guide.

When the AI co-host is on, what the host types about the room's decisions is sent to Anthropic under your API account terms. A line the co-host writes is shown on the room screen only after a deterministic check finds no number, identifier, or duration that the approved exercise does not contain. Leave the key out, or pass `--no-ai`, to keep the session entirely on the laptop.

## Data handling

- `.env`, `uploads/`, and `out/` are gitignored from the first commit. Keys, exports, pulled data, uploaded plans, and generated exercises for real organizations stay there.
- `ttx seed --save` writes only to `uploads/`.
- Only synthetic samples ship in the repository: the Valley Regional intake, estate, IR plan, org plan, and sample run.
- Uploaded documents are parsed locally (python-docx, pypdf) and are never written anywhere except the output path you name.
- No generator embeds secrets, keys, or environment variables in any document.

## Secret scanning

The repository is scanned with gitleaks across the working tree and the full git history before each submission.

## Reporting a vulnerability

Open a private security advisory on the GitHub repository (Security tab, "Report a vulnerability"). Do not open a public issue for a security problem.
