# Claude to ChatGPT Migration Plan: Five Scheduled Runs

Prepared 2026-10-20 for Dr. Josh Winowiecki. Sources: live definitions of all five scheduled tasks pulled from Claude today, the synced `calendar-sync` and `sunday-reset` skill files, and OpenAI's current documentation at learn.chatgpt.com (full source list at the end).

Working assumptions: you stay on Notion as the system of record and keep the Mac mini as the calendar drop point. You have not yet chosen a ChatGPT plan; I recommend one in Section 8.

---

## 1. Recommendation

Migrate in four waves over about three weeks, ordered from lowest to highest risk: Weekly Wins, then Afternoon Edition, then Calendar Sync and Sunday Reset together, then the Morning Brief last. Before any wave, run a one-evening verification gate (Section 6). Two facts decide whether this migration works, and OpenAI's public docs don't settle either of them:

1. **Notion tool parity.** All five runs depend on SQL-style queries against `collection://` data sources and on Notion's enhanced-markdown callout syntax. Notion publishes a plugin in ChatGPT's directory. Nothing public confirms that it exposes the same `notion-query-data-sources` and `notion-update-page` tools, or the `notion://docs/enhanced-markdown-spec` resource, that your prompts call by name.
2. **Custom MCP on your plan.** OpenAI's docs say ChatGPT web uses remote MCP servers only through plugins, and that "account and workspace policies apply to adding and using custom MCP servers." Third-party sources conflict on whether Plus allows custom servers with write actions. The Morning Brief needs at least four custom servers.

If either test fails, the Notion-only runs can still move. The Morning Brief would then need a rebuild around public APIs, as Section 4 describes.

The structural change I recommend is to **move each routine's canonical prompt into a Notion page and make every ChatGPT task a thin loader that fetches it.** Your CalendarSync and Sunday Reset skills already follow this pattern ("fetched live every run so Notion stays the single source of truth"). Today the three Code runs keep their full prompts inside Claude's scheduler, which is why moving them means copying 120,000 characters by hand. Under the loader design, a future move back to Claude, or to any other provider, costs about one paragraph per routine.

---

## 2. Inventory: what is moving

| Routine | Claude schedule (as stored) | Local time today (EDT) | Local time after Nov 1 (EST) | Model | Runtime | Tools | Writes | Notify |
|---|---|---|---|---|---|---|---|---|
| The Brief (Morning Digest v2.5.1) | `5 8 * * *` UTC, daily | 4:05 AM | **3:05 AM** | Sonnet 5 | ~12 min | Notion, PubMed, bioRxiv, Clinical Trials, AccuWeather, Anara, Granted, OpenAlex, Scholar Gateway, Unsplash, web search | 1 Brief Archive page; Blocks 1 to 4 of The Brief landing page | Off |
| Afternoon Edition v1.2 | `15 20 * * 1-4` UTC, Mon to Thu | 4:15 PM | **3:15 PM** | Sonnet 5 | ~8 min | Notion only | 1 Archive page; Blocks 1 and 2 of landing page | Push |
| Weekly Wins (G) | `0 21 * * 5` UTC, Fri | 5:00 PM | **4:00 PM** | Sonnet 5 | ~4 min | Notion only | 1 Notes entry (Type = Weekly Wins) | Off |
| Calendar Sync | Wed 7:00 PM America/Detroit | 7:00 PM | 7:00 PM | Sonnet 5.5 | <1 min when no PDF | Notion; Mac mini shell (`pdftotext`, `mv -n`) | Shadow Calendar rows, Last Synced stamps, CalendarSync Last Invoked, PDF move | Push |
| Sunday Reset | Sun 7:00 PM America/Detroit | 7:00 PM | 7:00 PM | Sonnet 5 | <1 min when no PDF | Notion; Mac mini shell; CalendarSync and TaskRealign Notion skills | Shadow Calendar, Sunday Reset Queue, 1 Maintenance Log row, Last Invoked, PDF move | Push |

Three findings came out of the inventory. None of them depends on the migration.

- **The UTC crons will drift on November 1.** The three Code runs are stored in UTC without `CRON_TZ`, so when daylight saving ends, each fires an hour earlier in Detroit. The Afternoon Edition would land at 3:15 PM, before your planning window. Whatever you decide about the migration, either add `CRON_TZ=America/Detroit` to these three in Claude this week or accept the shift for the overlap period.
- **The Code-versus-Chat split doesn't match the actual technical boundary.** In Claude, all five are cloud scheduled tasks on the same infrastructure; Calendar Sync and Sunday Reset just came from Cowork with the `~/Desktop/Claude` folder attached. The boundary that matters for ChatGPT is whether a run **needs the Mac mini's file system**. The two calendar runs do; the other three don't. The plan is organized around that boundary.
- **Weekly Wins has two latent defects.** Its prompt still contains the literal placeholder `[INJECT DATE ...]`, and it has no duplicate check, unlike the Afternoon Edition's Step 0.5. Today it works because the model infers the date. During a migration, both providers might fire on the same Friday, and without a duplicate check that produces two Weekly Wins notes. Fix both while porting it.

---

## 3. What ChatGPT offers in October 2026

OpenAI reorganized its product this year, and most 2025 guides are now wrong. These points come from learn.chatgpt.com, OpenAI's consolidated documentation site. I mark each one with how firmly the docs establish it.

**Surfaces.** ChatGPT now has three modes. *Chat* is conversation. *ChatGPT Work* is delegated task execution that produces files, research, or recurring updates. *Codex* is software work. Work and Codex share one usage pool. A fourth product, *dots*, is an always-on personal agent with its own cloud computer, built on GPT-6 Astra; it is rolling out only to Pro ($100/$200/$500), Business Premium, and Enterprise. (Established.)

**Scheduled tasks** are the direct equivalent of your Claude scheduled tasks. (Established, except where noted.)
- They can be created from Chat or Work on the web, or from Work or Codex in the desktop app, and are managed in a **Scheduled** view.
- *Standalone* tasks start a fresh chat on each run, which matches your current Claude behavior (`persist_session: false`). *In-chat* tasks return to one chat and keep its context.
- Cadence options: daily and weekly schedules, custom controls, and RFC 5545 RRULEs for advanced schedules. The Help Center reportedly caps recurrence at once per hour. (Help Center snippet only; the page returned 403 to direct fetch.)
- **Web tasks** run in the cloud and can use uploaded files, connected tools, plugins, and skills bundled in plugins. They "can't work directly in a folder on your computer."
- **Desktop-app tasks** can run in a local project folder. "Keep the computer on and the app running when a scheduled task needs local files." They run unattended under your default sandbox settings with `approval_policy = "never"`.
- **Active task caps by plan:** 3 on Free and Go, 5 on Plus, 10 on Business and Edu, and 15 on Pro and Enterprise. (Help Center via search snippet; Plus = 5 confirmed, Pro = 15 from third parties. Medium-high confidence.)
- **Notifications:** on the web, Settings > Notifications offers push, email, or SMS depending on category. On desktop, the Scheduled view acts as an inbox with unread indicators. The docs don't say whether a *desktop-local* task can send a phone push. (Gap; test it.)

**Skills** use the same open agent-skills `SKILL.md` format your Claude skills use. Standalone skills work only in the desktop app, Codex CLI, and IDE extension. To use a skill in a *web* scheduled task, you must bundle it in a plugin. A desktop task prompt can invoke a skill explicitly with `$skill-name`. (Established.)

**Plugins** replaced "apps" and "connectors" in July 2026. A plugin can bundle skills, MCP servers, and hooks. Notion appears in the directory ("Create docs, tasks, databases"), and Notion supports Sign in with ChatGPT. You add a custom MCP server through Plugins, the + button, then **Add custom MCP server**. Plugin hooks don't run in cloud Work. (Established; tool-level detail on the Notion plugin is not public.)

**Import from Claude.** The desktop app's Settings > Import pulls from Claude Code and Claude Cowork: instruction files (CLAUDE.md to AGENTS.md), settings, skills, plugins, project folders, MCP server configuration, hooks, slash commands, subagents, and chats from the last 30 days. **It doesn't list scheduled tasks**, so you rebuild all five by hand. Imported MCP servers land in the *desktop/Codex* configuration (`~/.codex/config.toml`), which web scheduled tasks don't read. (Established.)

**Models.** GPT-5.5 retired from Codex and Work sign-in on October 14, 2026. The current recommendation is **GPT-6.1 Sol** (`gpt-6.1-sol`) for complex agentic work and **GPT-6 Luna** for "focused, repeatable tasks." GPT-6 Astra is the top tier. (Established.)

---

## 4. Capability gap map

| Claude dependency | ChatGPT equivalent | Confidence | If it fails |
|---|---|---|---|
| Notion MCP (`mcp.notion.com/mcp`): fetch, SQL query of `collection://` sources, create/update pages | Notion plugin from the directory, or the same URL added as a custom MCP server | **Unverified on tool parity** | Add `https://mcp.notion.com/mcp` as a custom MCP plugin to get Notion's own tool set; if your plan blocks custom MCP, rewrite queries to whatever the plugin exposes |
| `notion://docs/enhanced-markdown-spec` (an MCP *resource*, not a tool) | No documented MCP resource support in ChatGPT | Low | Copy the callout, color, and heading syntax your prompts use into a `references/notion-markdown.md` file inside the skill; your canonical block examples already carry most of it |
| PubMed (`pubmed.mcp.claude.com`) | **None. Anthropic-hosted.** | n/a | NCBI E-utilities (public REST, no key below 3 requests/second) called from a skill script, or web search restricted to pubmed.ncbi.nlm.nih.gov |
| bioRxiv/medRxiv (`hcls.mcp.claude.com/biorxiv`) | **None. Anthropic-hosted.** | n/a | api.biorxiv.org (public REST) |
| Clinical Trials (`hcls.mcp.claude.com/clinical_trials`) | **None. Anthropic-hosted.** | n/a | ClinicalTrials.gov API v2 (public REST) |
| AccuWeather (`mcp.accuweather.com/v0/mcp/claude`) | The URL path is Claude-specific; no ChatGPT plugin found | Low | National Weather Service API (`api.weather.gov`, free, no key) for Detroit; it also returns active alerts, which Step 5 asks for |
| Anara (`anara.com/api/mcp`) | Custom MCP plugin with the same URL | Medium | Drop the "already in your collections" check from Signal Scan and Sense-Making; flag items as "not checked against Anara" |
| Granted (`grantedai.com/api/mcp/mcp`) | Custom MCP plugin | Medium | Web search on grants.gov, NIH Guide, HRSA, RWJF, and AHRQ (the prompt already names these) |
| OpenAlex (`openalex.caseyjhand.com/mcp`, a community server) | Custom MCP, or the public OpenAlex API directly | High (via API) | api.openalex.org; it's simpler and better supported than the community server |
| Scholar Gateway (`connector.scholargateway.ai/mcp`) | Custom MCP plugin | Medium | Web search; you lose nursing-literature coverage that PubMed under-indexes |
| Unsplash (`mcp.unsplash.com/mcp`) | Custom MCP plugin | Medium | Skip the cover image (the prompt already degrades cleanly) |
| Web search | Built in | High | n/a |
| Mac mini shell via Claude remote-devices (`device_bash`) | ChatGPT desktop app on the Mac mini, scheduled task in a local project | High | dots with a connected computer (Pro or Business Premium only) |
| Push notification at end of run | Web: push or email per Settings > Notifications. Desktop-local: Scheduled inbox; phone push not documented | Medium | Have the run write its one-line status to a Notion "Run Log" page you check, or send it through the Apple Messages plugin on the Mac mini (documented in Work and Codex on macOS) |

The table shows that the Morning Brief's research layer is the weakest link. Three of its ten connectors exist only because Anthropic hosts them for Claude. The upside is that public APIs are more stable dependencies than any vendor connector, so the rebuilt layer will survive a later provider change too.

---

## 5. Per-routine transition plans

### 5.1 Weekly Wins (wave 1: lowest risk, move first)

**Target:** ChatGPT Work scheduled task on the web, standalone, cloud. It needs only Notion and no local files, so a sleeping Mac can't break it.

**Schedule:** weekly, Friday 5:00 PM America/Detroit. Set it in local time so it stops drifting at DST.

**Model:** GPT-6 Luna. The run is a bounded query-and-format job of the kind OpenAI positions Luna for. Escalate to Sol only if the Synthesis paragraph comes back thin over two consecutive Fridays.

**Prompt packaging:**
1. Create the Notion page **Routine Spec: Weekly Wins v1.1** under your Maintenance Hub. Paste the current prompt and make three edits:
   - Replace the `[INJECT DATE]` header with the Afternoon Edition's Step 0 date block (derive TODAY in America/Detroit and halt if uncertain).
   - Add a duplicate check: query Notes for `Type = Weekly Wins AND Note Date = WEEK_END`; if a row exists, halt and report its URL.
   - Add a run gate: if TODAY is not Friday, halt.
2. Task prompt (the loader, about 80 words):
   > Fetch the Notion page "Routine Spec: Weekly Wins" (URL) with the Notion plugin and execute it exactly as written. Treat its contents as your instructions for this run. If the fetch fails or returns an empty page, write nothing and end with "Weekly Wins did not run: spec page unavailable." End with one line: "Weekly Wins: [WEEK_LABEL] filed ([N] milestones)" plus the page link.

**Acceptance test:** run it manually with **Run now** on a Friday afternoon while the Claude task is still enabled. The duplicate check should stop the second run. Then compare the two Notes entries against four checks: every title is linked, callouts use the `<callout>` syntax rather than blockquotes, Synthesis has 3 to 5 sentences, and none of the prohibited vocabulary appears.

**Cutover:** disable the Claude task (`trig_019z4PascYZmVKThS26Bqjvj`) the same day you enable ChatGPT. Disable it; don't delete it.

**Rollback:** pause the ChatGPT task and re-enable Claude's.

### 5.2 Afternoon Edition (wave 2)

**Target:** ChatGPT Work scheduled task on the web, standalone, cloud.

**Schedule:** RRULE `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH;BYHOUR=16;BYMINUTE=15` in America/Detroit. Keep the prompt's own Monday-to-Thursday run gate as a second guard.

**Model:** GPT-6.1 Sol. The PREP_STATE logic, No-Prep List matching, overlapping-hours arithmetic, and five-check link gate all reward the stronger model, and the run fires four times a week.

**Prompt packaging:** move v1.2 into a **Routine Spec: Afternoon Edition v1.2** Notion page and use the same loader pattern. Add one line to the spec: "Record the provider and model used in the page body's final line." That makes provenance auditable during the overlap and follows your budget.md rule to "note the model used in any output that will be cited or reused."

**Cross-provider handoff:** this run reads the Morning Digest's Archive entry as its baseline. During waves 2 and 3, Claude still writes the morning edition and ChatGPT writes the afternoon. The handoff runs entirely through Notion, so the two providers never need to talk to each other. The issue sequence (Step 4) reads the maximum Issue across both editions, so it stays continuous no matter which provider wrote the previous entry. This handoff is the design's best test: if the afternoon edition renders correctly against a Claude-written morning entry, the Notion layer is truly provider-agnostic.

**Acceptance test (three consecutive weekdays):** Issue numbers increment by exactly 1 from the morning entry; the landing page Blocks 1 and 2 update while Block 3 stays untouched; the duplicate check halts a manual re-run; Tomorrow, Pushed callouts carry the right PREP_STATE colors.

**Push notification:** enable task notifications under Settings > Notifications. Add to the loader: "End with one line suitable as a phone notification: 'Afternoon Edition #[ISSUE]: [N] closed, [N] due today, tomorrow [N] meetings ([N] need prep).'"

**Cutover and rollback:** same as Weekly Wins, with `trig_01XLcP2Bs3RciKY9hpcgaTsL`.

### 5.3 Calendar Sync and Sunday Reset (wave 3: move together)

These two belong in one wave because they share the drop folder, the CalendarSync Notion skill, the `processed/` naming convention, and the Shadow Calendar. If one provider runs Wednesday and another runs Sunday, the two can't conflict on data (CalendarSync is idempotent), but troubleshooting gets harder.

**Target:** the ChatGPT desktop app **on the Mac mini**, scheduled tasks in a local project rooted at `~/Desktop/Claude`, in Work mode. This setup is simpler than the current one: Claude runs in the cloud and reaches the Mac mini through remote-devices, while ChatGPT would run on the Mac mini itself.

**Setup on the Mac mini (one session, about 45 minutes):**
1. Install the ChatGPT desktop app and sign in. In System Settings > Energy, set the Mac mini never to sleep, set the app to open at login, and confirm it survives a restart.
2. Run **Settings > Import > Claude Cowork**. Select the `calendar-sync` and `sunday-reset` skills, the CLAUDE.md instruction file, and the Notion MCP configuration. Skip the chats; your record lives in Notion.
3. Open each imported `SKILL.md` and make these edits:
   - Replace "device_bash path `$HOME/mnt/Claude/inbox/calendar/`" with the local path `~/Desktop/Claude/inbox/calendar/`. The remote-mount indirection no longer applies.
   - Replace "send Josh a push notification" with the notification channel you confirmed in the verification gate.
   - Change nothing else. Both skills already defer every substantive rule to the live Notion pages, so the import should be clean.
4. Install `pdftotext` (`brew install poppler`) if Claude was using a copy staged elsewhere.
5. Set the project's sandbox to **workspace-write** with the project root at `~/Desktop/Claude`. Add rules that allow exactly `pdftotext` and `mv -n` within `inbox/calendar/`. Don't use full access: OpenAI's docs warn that background tasks with full access "carry elevated risk."
6. Confirm the Notion tools work *inside* this sandbox. The docs say read-only and workspace-write modes block network access, but they don't say whether plugin or MCP tool calls count as network for that rule. Test it before scheduling (Gate test G4).

**Task prompts:** reuse your current Claude prompts nearly verbatim. They're already short wrappers. Swap "Run the calendar-sync skill" for `$calendar-sync` and "Use the sunday-reset skill" for `$sunday-reset` so invocation is explicit. Keep the hard limits word for word: never write to Tasks, Projects, or the Pipeline; never delete; stop and report on every "ask Josh" point.

**Schedules:** Calendar Sync on Wednesday at 7:00 PM, Sunday Reset on Sunday at 7:00 PM, both America/Detroit. Model: GPT-6.1 Sol. The UTC conversion and fuzzy matching by title, join link, and organizer reward the stronger model, and these runs are short.

**Acceptance test:** drop a real Outlook export on a Wednesday, run **Run now** with the Claude task disabled, and check these points: the counts line matches the Notion skill's Step 5 format; every Scheduled and Cancelled row in the window carries a Last Synced stamp and no Happened row does; the PDF lands in `processed/` with the right name; Last Invoked updates on the CalendarSync row in the Skills library rather than the retired database. For Sunday Reset, add three checks: Queue rows are Pending with the correct Week Of, exactly one Maintenance Log row exists, and nothing was written to Tasks.

**Failure mode to plan for:** if the Mac mini is off or the app has quit, the run doesn't happen, and the docs don't describe a missed-run notice. Mitigation: the Monday Morning Brief already reads Sunday Reset's Maintenance Log row (Step 3.6). Add one line to that section: "If no Sunday Reset log row exists for this week, render 'Sunday Reset did not run' in the Summary Bar." That turns a silent failure into a visible one with no new infrastructure.

**Cutover and rollback:** disable `trig_01Hz6VTw6D3NqUKJiTCademk` and `trig_01WaZQHNu7WjucvoDNdnJ6We` together.

### 5.4 The Brief, Morning Digest (wave 4: move last)

This run is the hardest to move: an 86,573-character prompt (2,359 lines), eleven tool sources, day-of-week branching across seven templates, and a 12-minute runtime. It moves last for two reasons. It depends on the gate results more than anything else, and the other three waves will tell you how ChatGPT behaves on your Notion workspace before your most-read output is at risk.

**Target:** ChatGPT Work scheduled task on the web, cloud. The run needs no local files, and running it in the cloud keeps the 4 AM job independent of the Mac mini.

**Schedule:** daily at 4:05 AM America/Detroit (or later; see the push below). Model: GPT-6.1 Sol. Under budget.md's "cheapest adequate model" rule, Luna is tempting, but the Sense-Making, Signal Scan, and Conversation sections are judgment tasks. Try Luna on weekend runs, which are lighter, and compare.

**Prompt restructuring (required):** an 86K prompt plus eleven tool sources risks context pressure on any provider, and OpenAI doesn't document a prompt-length cap for scheduled tasks. Split the spec into Notion pages so each run loads only what it needs:
- **Core**: Steps 0 to 3.6, link rules, formatting rules, the write scope, the output steps, and the link gate. Every run loads it.
- **Day modules**: one page per day type (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday) holding only that day's sections and calibration.
- **Research layer**: Step 4 rewritten around the sources that survive the gate.

The loader fetches Core plus today's module. A Tuesday run would then load about 30% of today's prompt. That cuts cost under any provider and confines a bad edit to one day's template.

**Research layer rebuild:** package a skills-only personal plugin, "Brief Research," using Plugin Creator. Web tasks can invoke skills only through plugins. It contains:
- `pubmed_search` via NCBI E-utilities (`esearch` + `esummary`, last 24 hours, nursing and critical-care MeSH filters)
- `biorxiv_recent` via api.biorxiv.org for medRxiv health-sciences categories
- `trials_recent` via ClinicalTrials.gov API v2 (newly posted, nursing-relevant conditions)
- `openalex_trajectory` via api.openalex.org (citation counts by year for a concept)
- `nws_detroit` via api.weather.gov (forecast for gridpoint DTX plus active alerts)

All five are public, keyless or free-key REST APIs. If cloud Work containers can make outbound HTTPS calls (Gate test G5), these run as scripts. If not, Plugin Creator can host them as one small MCP server on ChatGPT Sites. Anara, Granted, Scholar Gateway, and Unsplash are added as custom MCP plugins with their existing URLs, provided Gate test G3 passes.

**Shadow week (required):** for 5 to 7 days, run the ChatGPT version with its write scope redirected to a **Brief Archive (Shadow)** test database. It must not touch the landing page or the issue sequence, which avoids issue-number collisions. Each morning, compare the shadow output against Claude's live edition on four dimensions: link completeness, template fidelity on that day's sections, research quality (are the Signal Scan items real, recent, and correctly framed), and the absence of prohibited vocabulary and em dashes. Cut over only after three consecutive passing days covering at least one Monday and one Wednesday, because those carry the most branching.

**Cutover:** switch the write targets back to production in the spec, then enable the ChatGPT task and disable `trig_01ChJkfq8B1X8PXsbJAuNTL8` on the same day. Afternoon Edition's baseline lookup needs no change.

**Push:** the Claude version has notifications off. Consider adding a one-line push in ChatGPT ("The Brief #[N]: [N] tasks, [N] meetings, [N] deadlines") only if you'd read it before opening Notion. Otherwise leave it off.

---

## 6. Verification gate (one evening, before wave 1)

Run these tests in an ordinary ChatGPT Work chat, not a scheduled task. Record pass or fail for each. Each failure has a predefined fallback, so no failure ends the migration.

| # | Test | Pass condition | If it fails |
|---|---|---|---|
| G1 | Install the Notion plugin. Ask it to fetch The Brief landing page by URL. | Page title "The Brief" and its block structure come back | Stop; nothing migrates until Notion works |
| G2 | Ask it to run Afternoon Edition Step 2 Sub-Query E (task count) against `collection://413a4a23-…` | Returns a count matching today's Claude afternoon entry | Add `https://mcp.notion.com/mcp` as a custom MCP plugin (G3) and retest; if that's blocked too, rewrite queries to the plugin's native tool set (adds about 2 days to the plan) |
| G3 | Plugins > + > **Add custom MCP server** with `https://anara.com/api/mcp` | Option exists on your plan; OAuth completes; tools list | Morning Brief drops the Anara check; Notion stays on the directory plugin |
| G4 | In the desktop app on the Mac mini, in the `~/Desktop/Claude` project with workspace-write, run `pdftotext -layout` on an old export and then a Notion read | Both succeed without a prompt | Allowlist the network for the Notion domain via rules, or move the Notion steps into a web task that the local task hands off to |
| G5 | In a cloud Work chat, ask it to run a script that calls `https://api.weather.gov/points/42.33,-83.05` | JSON returned | Host the research tools as a Sites MCP server |
| G6 | Create a throwaway web scheduled task for 10 minutes out, with notifications on | Phone push arrives | Use the Notion Run Log page as the status channel |
| G7 | Paste the full Morning Digest Core spec plus one day module into a Work chat and ask for a summary of Step 3.5 | Accurate summary; no truncation warning | Split the spec further |

Budget: about 90 minutes and a small number of Work messages.

---

## 7. Timeline

| Week of | Action | Claude state after |
|---|---|---|
| Oct 20 (now) | Add `CRON_TZ=America/Detroit` to the three Claude Code runs, regardless of the decision. Create the four Routine Spec pages in Notion. | 5 active |
| Oct 26 | Gate tests G1 to G7. Wave 1: Weekly Wins cuts over Friday Oct 30. Set up the Mac mini app. | 4 active |
| Nov 2 | Wave 2: Afternoon Edition shadow Mon to Tue, cutover Wed Nov 4. Wave 3: Calendar Sync on Wed Nov 4, Sunday Reset on Sun Nov 8. | 1 active |
| Nov 9 | Wave 4: Morning Brief shadow week (Nov 9 to 15). | 1 active |
| Nov 16 | Morning Brief cutover on Monday Nov 16. All Claude tasks disabled, not deleted. | 0 active |
| Dec 1 | If ChatGPT has run clean for two weeks, export any Claude chats you want, then downgrade or cancel. | n/a |

Keep the disabled Claude tasks for at least 30 days. Re-enabling one costs a click; recreating it from scratch would mean rebuilding an 86K prompt.

---

## 8. Second-order consequences

**Plan choice.** Plus caps you at 5 active scheduled tasks: exactly these five, with no headroom. Supper Board's two tasks (currently disabled) and any future routine would exceed the cap. Pro starts at $100 per month, allows about 15 tasks, removes the five-hour usage window, and includes dots. Your current Claude spend is $20 (Pro), with Max at $100 recommended in budget.md. My recommendation: **start on Plus** for the gate and waves 1 to 3, and decide on Pro before wave 4. Base that decision on the Morning Brief's measured usage, which you can see in the usage dashboard after the shadow week, and on whether you want Supper Board migrated. Confidence: medium. OpenAI doesn't publish a per-message cost for scheduled Work runs, so only measurement settles it.

**What the migration doesn't cover.** Your stack documents (CLAUDE.md, lanes.md, budget.md, SETUP.md, and the Notion routing pages) assume Claude as the synthesis and drafting engine: argument architecture, section drafting, revision memos, voice QA. Moving the scheduled runs doesn't move that lane, and the Tri-Tool Protocol's November topology review is the natural place to decide it. One option worth naming: keep the scheduled runs on whichever provider is cheapest and most reliable for unattended Notion work, and decide the drafting lane separately on prose quality. These are different jobs, and nothing requires one vendor for both.

**Anara.** Anara Pro already gives you GPT 5.6 Sol, Opus 5, and Fable 5 inside the evidence layer. If you leave Claude entirely, Anara becomes your only path to Anthropic models, and that's worth knowing before you cancel.

**Maintenance burden.** The loader design adds four Notion pages and one small plugin, and it removes the need to edit prompts inside any provider's scheduler again. Version changes become Notion edits with page history, which suits your CalibrationNote discipline.

---

## 9. Remaining weaknesses

Read this plan as Reviewer 2 would, and two weaknesses survive. First, **the plan rests on two unverified facts** (Notion tool parity and custom MCP on your plan). The gate tests them cheaply, but until they run, the Morning Brief estimate (about one week of rebuild work) could be off by a factor of two. Second, **desktop-local tasks have no documented missed-run alert.** The Monday Summary Bar mitigation catches Sunday Reset failures, but a missed Wednesday Calendar Sync would show up only as the Afternoon Edition's existing "Shadow Calendar last synced" staleness note. That's acceptable, but it catches the miss late.

---

## 10. What I need from you, and the next two moves

**Decisions:**
1. Do you approve the loader design (canonical prompts in Notion)? Everything in Section 5 assumes it.
2. Which ChatGPT plan do you want for the gate: Plus as recommended, or Pro from the start?
3. Should I add `CRON_TZ=America/Detroit` to the three Claude Code runs now? It's a one-line change per task.

**Next two moves once you approve:**
1. I draft the four Routine Spec pages as Claude Working Drafts subpages in Notion, including the Weekly Wins fixes and the Morning Digest Core/day-module split, for your review.
2. I write the gate test script (G1 to G7) as a checklist you can paste into ChatGPT step by step, with exact prompts and expected outputs.

---

## Sources

Documentation was retrieved 2026-10-20. help.openai.com returned 403 to direct fetches, so Help Center figures come from search-engine snippets of those pages and are marked as such above.

- OpenAI. Scheduled tasks. learn.chatgpt.com. https://learn.chatgpt.com/docs/automations
- OpenAI. Model Context Protocol. learn.chatgpt.com. https://learn.chatgpt.com/docs/extend/mcp
- OpenAI. Plugins. learn.chatgpt.com. https://learn.chatgpt.com/docs/plugins
- OpenAI. Build skills. learn.chatgpt.com. https://learn.chatgpt.com/docs/build-skills
- OpenAI. Import from another agent. learn.chatgpt.com. https://learn.chatgpt.com/docs/import
- OpenAI. Notifications. learn.chatgpt.com. https://learn.chatgpt.com/docs/notifications
- OpenAI. Get started with ChatGPT Work. learn.chatgpt.com. https://learn.chatgpt.com/docs/get-started-with-work
- OpenAI. Meet dots; Tasks and memory; Connect computers and apps; Control your dot. learn.chatgpt.com. https://learn.chatgpt.com/docs/dots
- OpenAI. Models. learn.chatgpt.com. https://learn.chatgpt.com/docs/models
- OpenAI. Pricing. learn.chatgpt.com. https://learn.chatgpt.com/docs/pricing
- OpenAI. Remote connections. learn.chatgpt.com. https://learn.chatgpt.com/docs/remote-connections
- OpenAI. Computer Use. learn.chatgpt.com. https://learn.chatgpt.com/docs/computer-use
- OpenAI. Projects and chats. learn.chatgpt.com. https://learn.chatgpt.com/docs/projects
- OpenAI. Connect and test your plugin. developers.openai.com. https://developers.openai.com/plugins/deploy/connect-chatgpt
- OpenAI. Scheduled tasks in ChatGPT. Help Center (via search snippet). https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt
- OpenAI. ChatGPT agent. Help Center (via search snippet). https://help.openai.com/articles/11752874
- OpenAI. Developer mode and MCP apps in ChatGPT. Help Center (via search snippet). https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Notion plugin listing. ChatGPT Plugins directory (via search snippet). https://chatgpt.com/plugins/plugin_asdk_app_69c18c28f1188191bf5b8445c4ab0a2e
- Third-party, used only where flagged: Peliqan, ChatGPT MCP: plans, setup and what breaks in 2026 (https://peliqan.io/blog/chatgpt-mcp/); Carly, ChatGPT + Notion integration (https://www.usecarly.com/blog/chatgpt-notion-integration/); Android Headlines, ChatGPT's task scheduling feature is now free (https://www.androidheadlines.com/2026/08/chatgpts-task-scheduling-feature-is-now-free-but-not-without-limits.html).
