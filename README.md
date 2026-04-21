# RapidLocalSites Agent

Automated pipeline that finds local businesses without a website, generates a preview site, deploys it to Vercel, and creates a Gmail draft to pitch the owner.

Runs as a Claude Routine (Claude Code on the web) twice per night. State lives in Supabase. Preview URLs live 14 days before cleanup.

## Layout

```
main.py                    CLI entrypoint: --batch A|B | --cleanup | --test <slug> | --dry-run
agents/                    Pipeline stages (search → scrape → classify → generate → deploy → email)
utils/                     Supabase client, dedup, design seed, logger
templates/
  design_tokens.json       category → palette/typography/hero DNA
  content.schema.json      per-customer content contract (drives the generated site)
  layouts/*.json           per-category structural skeletons (section order, components, CTA)
  prompts/*.md             Opus/Haiku/Sonnet prompts
supabase/schema.sql        Tables + RLS policies (prospects, customers, content, drafts, runs, assets)
deliver.py                 Run manually after a signed contract: moves content into Supabase
                           `content` table and sends the magic-link to the owner
```

## Local usage

```bash
cp .env.example .env   # fill in secrets
./setup.sh
python main.py --test salon-krasa-praha     # single-site dry-ish run
python main.py --batch A --count 2           # batch of 2 (what Routines runs)
python main.py --cleanup                     # 14d Vercel cleanup + 180d prospect archive
```

`--dry-run` skips the GitHub push, Vercel deploy, and Gmail draft – it prints the generated HTML to stdout.

## Routines

Two routines on claude.ai/code/routines, both using `claude-sonnet-4-6` as the main model and this repo as source:

| Routine | Cron (Europe/Prague) | Prompt |
|---|---|---|
| `nightly-batch-A` | `0 22 * * *` | `python main.py --batch A --count 2` |
| `nightly-batch-B` | `5 3 * * *` | `python main.py --batch B --count 2 && python main.py --cleanup` |

Required connectors: **GitHub**, **Gmail**. Enable "Allow unrestricted branch pushes" so the pipeline can push to `main` of per-customer `preview-*` repos.

Env vars (see `.env.example`): `GITHUB_TOKEN`, `VERCEL_TOKEN`, `GOOGLE_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `BATCH_NAME`, `GMAIL_SENDER`.

## Supabase schema

Initialize once:

```bash
psql "$SUPABASE_URL" -f supabase/schema.sql
```

or paste into the SQL Editor on supabase.com. RLS policies let a logged-in customer read/write only their own `content` and `assets` row; the server uses the service-role key which bypasses RLS.
