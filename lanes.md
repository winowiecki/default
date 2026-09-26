# Lanes: which pane owns which work

Divide by pipeline stage, not task type. Evidence flows from Anara, synthesis and drafting happen in Claude, Notion holds the record. Each artifact has one canonical home.

| Task | Pane | Model tier | Output lands | Notes |
|---|---|---|---|---|
| Ideation, brainstorming, competing framings | Claude | Opus/Fable for the framing pass, Sonnet for the write-up | Pipeline Idea row (draft) | `prompts/01` |
| Argument architecture, claim ladder, reviewer objections | Claude | Opus/Fable | Working Drafts subpage | `prompts/02`; reads Anara collection live |
| First drafts of manuscript sections | Claude | Sonnet, escalate for conceptual sections | Working Drafts subpage | `prompts/03`; SectionDraft in Notion is the fallback |
| Revision memo after a Notion voice pass | Claude | Sonnet | Working Drafts subpage | `prompts/04` |
| Voice QA (read-aloud audit) | Claude | Sonnet | Chat table or `outputs/` | `prompts/05`; this replaces Notion Fable voice passes |
| Decision archaeology, commitment tracking across Notes | Claude | Sonnet | Notes entry, Type Synthesis | `prompts/06` |
| Meeting prep (1:1, committee) | Claude | Sonnet | Notion prep note from template | `prompts/07`, `prompts/08` |
| Anara pass design | Claude designs, Anara executes | Sonnet to design; Kimi/GLM in Anara for extraction, Opus/Fable in Anara for interpretive passes | Anara outputs, then exported to Pipeline evidence subpage | `prompts/09` |
| Overlap audit across companion papers | Claude | Sonnet | Lead paper's Working Drafts | `prompts/10` |
| Seminar case build (NUR 932/935) | Claude | Sonnet | Teaching Portfolio course subpage | `prompts/11`; ModuleBuilder and SlideBuilder stay in Notion |
| Calibration capture | Claude drafts, Notion applies | Sonnet | Proposed edit only | `prompts/12` then CalibrationNote in Notion |
| Grant aims and narrative | Claude | Opus for aims, Sonnet for narrative | Grant Tracker entry, Working Drafts subpage | `prompts/13`; GrantDraft in Notion keeps budget justification, letter requests, Tracker writes |
| Reviewer response (triage, plan, letter) | Claude | Opus for triage, Sonnet for letter | Pipeline Working Drafts subpage | `prompts/14`; ReviewRespond in Notion for the Pipeline write step if wanted |
| Voice pass on the draft of record | Notion (Norman) | Mid-tier; Fable only for the final pass | Draft of record | Notion-only because it edits the record |
| Email drafting | Notion, EmailDraft | Mid-tier | Notes, People touchpoints | Updates People on every draft; do not port |
| Meeting wrap-up, tasks, People updates | Notion, MeetingWrapUp | Mid-tier | Notes, Tasks, People | Transcription is free |
| Social posts | Notion, PostDraft | Mid-tier | Posts database | Separate voice guide |
| Student grading | Notion, GradeAssist | Mid-tier | Grading Log, Grading Patterns | Record-writing |
| Slides, recorded modules | Notion, SlideBuilder, ModuleBuilder | Mid-tier | Deck or module pages | Reads Presentation Voice & Style |
| Resource capture, CV sync, dossier, CE log, week planning, task realign | Notion skills | Mid-tier | Their databases | Record-writing |
| Corpus interrogation, extraction matrices, contradiction maps, coding | Anara | Kimi/GLM default; Opus/Fable for interpretation | Anara outputs; exported to Notion evidence subpages | Passage anchoring is the hallucination control |
| Deep Search over a corpus | Anara Max 5x (sprint months only) or Anara credits | Fable/Opus | Same | Tactical upgrade |
| Daily digest, weekly wins | Claude Code | Cheapest adequate model | Notion archive pages | `automations/` |
| Workspace audits (Routines A to N) | Notion agent | Mid-tier | Maintenance Log | Reduced frequency per SETUP Step 3 |

## Overflow order (fixed)
- Claude caps: buy Claude usage credits, or wait for the window. Never move drafting into Notion.
- Notion caps: queue record-writing work; move any drafting or judgment pass to Claude. Use Notion credits only for time-critical record writes.
- Anara caps: buy Anara credits (they roll over). Never move corpus work into Claude or Notion.
