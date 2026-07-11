# PDF Downloads

PaperAgent can fetch a paper PDF by DOI, ingest it, and attach it to a chat
session so the agent can use the paper as session context.

## How It Works

1. The user selects or starts a chat session.
2. The user opens the `Downloads` tab or clicks a `Get PDF` DOI chip in chat.
3. The frontend sends the DOI and `session_id` to `POST /api/v1/downloads`.
4. The backend validates and normalizes the DOI.
5. A `download_jobs` row is created unless an active job for the same user and DOI
   already exists.
6. The background worker fetches the PDF from the configured provider.
7. On success, the PDF is saved under the session upload directory, ingested into
   the vector store, and added to the session file list.
8. The frontend polls `/api/v1/downloads?session_id=...` and shows job status.

The provider token stays server-side. The frontend never receives it.

## Frontend Entry Points

There are two ways to request a PDF:

- `Downloads` tab in the top header: paste a DOI and queue a download for the
  current session.
- `Get PDF` chip under a chat message: shown when the UI detects a DOI in a user
  or assistant message.

The `Downloads` tab is session-scoped. A session must exist before a download can
be queued, because the ingested PDF needs a conversation to attach to.

## Backend API

### Queue a Download

```http
POST /api/v1/downloads
```

Body:

```json
{
  "session_id": "chat-session-id",
  "doi": "10.xxxx/example"
}
```

Returns the job, remaining quota, and whether the request was deduplicated.

### Get One Job

```http
GET /api/v1/downloads/{job_id}
```

Returns one ownership-checked job.

### List Session Jobs

```http
GET /api/v1/downloads?session_id=chat-session-id
```

Returns all jobs for that session plus remaining quota.

## Job Statuses

- `QUEUED`: Waiting for the worker.
- `RUNNING`: The worker is fetching and ingesting the PDF.
- `RETRY_SCHEDULED`: A failed attempt was rescheduled for later.
- `SUCCEEDED`: Downloaded, ingested, and attached to the session.
- `FAILED`: Terminal failure.

Failure codes:

- `PDF_NOT_FOUND`: Provider returned 404 until retry attempts were exhausted.
- `PROVIDER_ERROR`: Provider error, invalid response, network error, or ingestion
  failure.

## Scheduling And Priority

Downloads are processed by one background worker, one job at a time.

Per user, within the quota window:

- Requests `1..3` are `FAST`.
- Requests `4..10` are `STANDARD`.

FAST jobs:

- Available immediately.
- Target deadline defaults to 60 minutes.
- Priority round is request number `1`, `2`, or `3`.

STANDARD jobs:

- Spread across the next 24 hours using configured offsets.
- Have deterministic per-user jitter so many users do not all become available at
  the same time.

The scheduler also has:

- Anti-starvation: after several FAST jobs, an eligible STANDARD job can run.
- Deadline urgency: FAST jobs close to their target deadline jump ahead.

## Limits

Default limits are configured in `.env.example` and `app/core/config.py`.

| Setting | Default | Meaning |
| --- | ---: | --- |
| `DOWNLOAD_QUOTA_LIMIT` | `10` | Max originating download requests per user per window |
| `DOWNLOAD_QUOTA_WINDOW_HOURS` | `24` | Rolling quota window |
| `DOWNLOAD_MAX_ATTEMPTS` | `3` | Max provider attempts per job |
| `DOWNLOAD_RETRY_DELAYS_MIN` | `10,20` | Delay before attempt 2 and 3 |
| `FAST_TARGET_MINUTES` | `60` | Target time for first three requests |
| `STANDARD_TARGET_HOURS` | `24` | Target time for standard requests |
| `STANDARD_OFFSETS_HOURS` | `1,5,9,12,16,20,24` | Standard job spread schedule |
| `SCHEDULE_JITTER_MINUTES` | `15` | Plus/minus jitter for standard jobs |
| `FAST_BEFORE_STANDARD` | `5` | Anti-starvation threshold |
| `DEADLINE_URGENT_MINUTES` | `10` | Urgency window for FAST jobs |
| `WORKER_POLL_SECONDS` | `5` | Worker idle poll interval |

Retries do not consume more quota. Duplicate active DOI requests for the same
user are deduplicated and do not consume more quota.

## Configuration

Required for real downloads:

```env
PROVIDER_BASE_URL=http://provide.falinoos.ir:8081
PROVIDER_TOKEN=your_provider_token
ENABLE_DOWNLOAD_WORKER=true
```

The worker requests:

```text
{PROVIDER_BASE_URL}/article/doi?token=...&doi=...
```

For local failure testing:

```env
ENABLE_DOWNLOAD_WORKER=true
DOWNLOAD_MAX_ATTEMPTS=1
WORKER_POLL_SECONDS=1
PROVIDER_TOKEN=
```

Then restart the backend:

```bash
docker compose up -d --force-recreate app
```

## Database

Jobs are stored in the `download_jobs` table.

The schema is represented by:

- `app/models/downloads.py`
- `migrations/20260711_add_download_jobs.sql`
- startup migration SQL in `app/core/database.py`

Important indexes:

- `ix_download_jobs_user_id`
- `ix_download_jobs_session_id`
- `ix_download_jobs_doi`
- `ix_download_jobs_status_available`
- `ix_download_jobs_user_created`

## Operational Notes

- Only one worker should run against a queue if strict one-at-a-time behavior is
  required.
- The provider token must never be exposed to the frontend.
- The UI polls every 4 seconds while active jobs exist.
- If a job succeeds, the file sidebar refreshes and the PDF becomes available to
  the agent through the session file context.
- If automatic retrieval fails with `PDF_NOT_FOUND`, the UI offers manual PDF
  upload or continuing without the full paper.
