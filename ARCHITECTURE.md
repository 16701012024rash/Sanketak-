# Sanketak — Architecture Note (On-Prem / Self-Hosted Framing)

## Core claim

Sanketak runs entirely on infrastructure OIL controls. No worker report, analysis result,
or HSE data is sent to a third-party cloud AI service. The system can be deployed inside
OIL's own network with a single command and no internet dependency for its core functions.

## What runs where

| Component                                           | Runs on                                                                                    | External calls?        |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------- |
| FastAPI backend                                     | OIL's server (Docker container)                                                            | None                   |
| PostgreSQL + pgvector                               | OIL's server (Docker container)                                                            | None                   |
| JWT auth (HSE login)                                | OIL's server, self-signed tokens                                                           | None                   |
| SIF prediction model (TF-IDF + Logistic Regression) | [PENDING CONFIRMATION — expected: runs locally alongside backend, no cloud inference call] | [PENDING CONFIRMATION] |

## Data flow

1. Worker submits a report (text, any language) → stored directly in OIL's own Postgres database.
2. Report text is analysed by the SIF model → result (risk probability, risk level) written back to the same database.
3. HSE staff log in with JWT-authenticated accounts stored in the same database, and view/query reports, patterns, and precedent matches — all served from local data, no external lookups.
4. Worker can check status anytime using only their anonymous token — no login, no PII stored.

## What data never leaves the OIL network

- Raw report text (potentially sensitive incident descriptions)
- Worker anonymous tokens
- HSE user credentials (hashed, never stored in plain text)
- Risk scores, patterns, and corrective action records

## How HSE staff can edit rules without redeploying code

Currently, detection categories (barrier categories, equipment tags) are defined in the
backend service layer (`app/services/analysis.py`). A future `/rules` CRUD endpoint (planned)
would move these into the database, so HSE admins can add/edit detection rules through the
API/dashboard without any code change or redeployment — directly demonstrating the
"rules editable by OIL's HSE team" capability live.

## Deployment

The entire stack (API + database) starts with a single command: `docker-compose up --build`

No external service accounts, API keys, or internet access are required for the system
to function end-to-end.

## Open item

Confirming with the AI/ML team that the SIF prediction model (TF-IDF + Logistic Regression)
runs as a local Python process/library call within the same infrastructure, with no calls
to an external inference API. Once confirmed, this note will be updated to state it as fact.
