# Setup: Cowork folder build (September 2026)

Follow these steps in order. Total time: about 40 minutes.

## Step 1. Back up and merge
1. Copy your current Cowork root folder to a dated backup (for example `cowork-backup-2026-09-05`).
2. Unzip this package. It mirrors your existing layout (`CLAUDE.md`, `context/`, `outputs/`, `projects/`, `templates/`) and adds `prompts/`, `automations/`, `logs/`, `lanes.md`, `budget.md`.
3. Copy the package contents over your root. Files that already exist in your root are handled as follows:
   - `CLAUDE.md`: REPLACE with the new version. Your hard rules and routing table are preserved inside it.
   - `context/about-me.md`, `context/people-orgs.md`, `context/voice-style.md`: KEEP yours. This package does not overwrite them. They become the offline fallback cache (see Step 4).
   - `templates/README.md`, `templates/extraction_prompt.md`, `templates/data_extraction_codebook.md`, `templates/CON template 1.pptx`: KEEP yours. New templates are added alongside.
   - `projects/*`: untouched. A `projects/_TEMPLATE/` folder is added.

## Step 2. Connectors
In Claude (desktop) confirm both MCP servers are attached to the Cowork session:
- Notion MCP (already connected).
- Anara MCP server (already connected in Claude Chat; confirm it is enabled for Cowork).
Test: ask Claude to fetch `https://app.notion.com/p/8817446e89a0464caa62ae82052c9d2c` and report the page title. Then ask it to list one Anara folder. If either fails, the session must not draft manuscript prose.

## Step 3. Notion-side changes (10 minutes, in Notion)
1. Swap in the compressed My Notion AI page (draft exists: "My Notion AI: Compressed Draft (Review Before Swap)").
2. About Dr. W: run the fall 2026 pass on "Active This Term" and "Academic Calendar". Routine H does not do this.
3. Settings, Notion AI: set the default agent model to a mid-tier model; reserve Fable for named passes.
4. Settings, Notion AI: toggle "Allow workspace to use Notion credits after AI limit is reached" ON, buy the smallest monthly credit pack.
5. Maintenance Hub: reduce Routine C to one weekly run; A and B to monthly; consolidate the eight monthly audits into two runs.

## Step 4. Cache refresh rule for the three context files you already have
Your `about-me.md`, `people-orgs.md`, and `voice-style.md` are July 23 exports and already drift (Summer 2026 term, Macy deadline). Add this line to the top comment of each:
`<!-- FALLBACK CACHE. Read the live Notion page first (see context/notion-map.md). Use this file only when the Notion connector is unavailable. -->`
Refresh them at semester boundaries only. Do not add new content to them; new content goes to Notion.

## Step 5. Project folders
For each active manuscript or project in `projects/`, add a `CLAUDE.md` copied from `projects/_TEMPLATE/CLAUDE.md` and fill in: Pipeline URL, Anara collection name, companion papers, current version, next gate. Start with: Queer Theory, DNP Knowledge Production, Formation vs. Competency, Practice Label, Virtual Care Paper 1, cns-on-call-study.

## Step 6. Automations
Open `automations/morning-digest/README.md` and `automations/weekly-wins/README.md`. Set the model tier and tool-call budget in your Claude Code job definitions to match. Confirm whether these jobs bill from the interactive pool or the separate non-interactive pool (Claude usage settings) and record the answer in `budget.md`.

## Step 7. First session test
Open a Cowork session in the root. Paste: `Run prompts/05-voice-qa.md on outputs/<any recent draft>.` Confirm it (a) checks lanes.md, (b) fetches Voice & Style live, (c) outputs a table without rewriting, (d) appends nothing to Notion. Then run `prompts/07-one-on-one-prep.md` for your next real meeting and confirm the prep note lands in Notion from the template.

## Step 8. Claude Chat Projects
Create one Claude Project per active manuscript. Project instructions: paste `prompts/_header.md` plus the project's `projects/<slug>/CLAUDE.md`. Attach nothing else; everything is read live.

## Step 9. Review cadence
- Weekly: skim `logs/friction.md`; route any rule change through CalibrationNote in Notion, never by editing `hard-rules.md` alone.
- Monthly: re-read `budget.md` against actual usage panels (Claude, Notion, Anara) and adjust `lanes.md` model tiers.
- November 2026: topology review per the Tri-Tool Protocol.
