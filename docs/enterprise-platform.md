# Enterprise inquiry platform

## What is implemented

The existing reference site remains generated HTML. A React component handles the inquiry form, built with esbuild. A Node/Fastify service serves only `_site/` and accepts `POST /api/inquiries`. PostgreSQL is the durable source of truth. Redis shares rate-limit counters across instances; it is not a second store for inquiry details. These are integration-ready components, not provisioned cloud infrastructure.

The form is disabled in a default static build. `CONTACT_API_URL=/api/inquiries npm run build` enables same-origin operation with the Node server. GitHub Pages can instead be built with an absolute HTTPS API endpoint via the repository variable `CONTACT_API_URL`. Pages cannot run the API or database. Do not set that variable until the API is deployed and the public contact/privacy details are finalized.

## Service choices

| Function | AWS deployment | Google Cloud equivalent | This change |
|---|---|---|---|
| React assets / public HTML | S3 + CloudFront, or existing Pages | Cloud Storage + CDN, or existing Pages | Built static assets; Pages publishing retained |
| Node API and optional frontend host | ECS Fargate behind an HTTPS load balancer | Cloud Run container | Dockerfile and container entry point |
| Durable inquiries | RDS for PostgreSQL | Cloud SQL for PostgreSQL | SQL migration and parameterized repository |
| Shared ephemeral counters / future cache | ElastiCache Redis OSS/Valkey | Memorystore for Redis | Redis rate-limit integration; no PII cache |
| Future private attachments | Private S3 bucket | Private Cloud Storage bucket | Design below; uploads not implemented |
| Secrets | Secrets Manager | Secret Manager | Environment contract, no cloud credentials embedded |

Recommended initial topology: keep the public site on Pages, deploy the API container in the selected cloud, and place PostgreSQL and Redis on private networks reachable only by that service. A same-origin reverse proxy is also supported if the whole site moves behind one domain. Account/project, region, domain and recurring budget are still needed before provisioning.

React is the browser UI library; Node/Fastify is the frontend/API server. Redis is a service, not an implementation language. S3 stores objects such as files; it does not replace PostgreSQL's queryable records.

## Submission behavior

- Required name, work email, organization, service, 20–5,000 character message and affirmative consent.
- Server validation is authoritative; the browser also validates required fields.
- UUID idempotency key + normalized-body hash: same retry returns the saved reference; changed data with the same identifier returns conflict.
- Success is returned only after SQL persistence. Database failure returns 503 and the browser keeps the form data.
- The response contains a reference ID, not stored personal information. No public list/read/update endpoint exists.
- Request bodies are limited to 16 KiB. Exact allowed origins, JSON-only requests, a honeypot and rate limits reduce abuse. Origin checks alone do not stop non-browser spam; add an edge WAF or challenge when production traffic warrants it.
- Requests are limited to five per ten minutes per client IP. Redis keys use an HMAC of the IP; this is pseudonymization, not a claim of irreversible anonymization. No submitted body or email is written to application logs.
- Never enable blanket proxy trust. Set `TRUST_PROXY` to the specific trusted proxy addresses/CIDRs after verifying the deployment's forwarding chain. Otherwise clients behind the same proxy may share one limit.
- `GET /healthz` is liveness; `GET /readyz` checks SQL and Redis. Redis failure makes the service unready and requests must not silently fall back to independent per-instance counters.

No customer emails or external notifications are sent. Inquiry triage currently requires a restricted database operator. Before public launch, assign a staffed triage process; a later authenticated admin UI or CRM delivery worker should use SSO and explicit authorization, with retries and delivery receipts.

## Run locally

```sh
npm ci
CONTACT_API_URL=/api/inquiries npm run build
npm test
npx playwright install --with-deps chromium webkit
npm run test:e2e
# Real PostgreSQL + Redis + web container:
docker compose up --build
```

Open http://localhost:3000 for Compose. Compose includes a one-shot migration job and persistent PostgreSQL volume; restarting the web container does not discard inquiries. Its passwords and HTTP settings are only for local use. Tests use synthetic `.invalid` emails, never customer data. Local API tests use PGlite (embedded PostgreSQL); CI browser tests use a PostgreSQL 17 service and Redis 7.

For an existing database, run `npm run db:migrate` as a deployment step with a migration role. Give the runtime role only SELECT and INSERT on `enterprise_inquiries`; status changes and retention belong to separately authorized operators. Use verified database TLS/private connectivity. The app refuses production startup without Redis, explicit HTTPS origins and a rate-limit secret of at least 32 characters.

## Cloud rollout sequence

1. Select AWS or Google Cloud, region, existing network, DNS name and budget. Choose backup retention and recovery objectives with the operator.
2. Create private managed PostgreSQL with encryption at rest, backups and point-in-time recovery. Enable deletion protection and test a restore before accepting customer inquiries.
3. Create private Redis with authentication and TLS (`rediss://`), reachable only by the API. Use an instance/service mode compatible with the client configuration; cluster mode is not configured by this change.
4. Build and publish the container to the chosen registry. Use a workload identity/service role and managed secret injection. Apply the schema with a separate deployment job, then start the non-root runtime.
5. Terminate TLS at the provider, configure exact allowed origins and trusted proxies, and verify readiness, rate limits and idempotent retry against staging.
6. Publish operator identity, business contact address and a chosen inquiry retention policy. Set up the deletion/correction route and triage ownership. These business details have not been invented in this PR.
7. Enable the frontend endpoint only after staging is verified. Test from the real public domain and monitor acceptance/error counts without logging message contents. Verify rollout/rollback and database restore procedures.

A proposed starting retention policy is to remove inactive, unconverted inquiries after 90 days, with exceptions for documented engagements or holds. This is a proposal requiring operator adoption; no background deletion job is enabled and no retention promise is made to visitors yet.

## Blob storage: planned second phase

The initial form accepts text only. Adding attachments requires a separate controlled flow:

1. Issue a short-lived upload grant tied to an accepted inquiry and a random object key, with file type and size restrictions.
2. Upload to a private quarantine bucket/prefix. Block public access, disable public ACLs, use encryption and TLS, and give the web runtime only the specific object permissions it needs.
3. Validate actual file type, size and checksum; scan before moving to an approved prefix. Never expose arbitrary executable files through the public site.
4. Store object metadata and the inquiry association in PostgreSQL. Deliver authorized downloads via short-lived grants; expire both original objects and old versions according to the adopted retention policy.

S3/Cloud Storage provisioning and the upload API are **not** implemented or enabled here. Keeping attachments out of the first intake avoids asking potential customers to upload confidential material before an engagement is established.

## Maintenance and release gate

Playwright exercises every published HTML page in desktop light/dark, mobile Chromium and mobile WebKit profiles. It checks navigation, runtime errors, viewport overflow, trait filtering/deep links, keyboard disclosures, no-JavaScript reading, form validation, successful persistence acknowledgments, rate-limit/network/storage errors and duplicate-click behavior. Axe checks key entry pages. Failure artifacts contain only synthetic data.

The reusable quality workflow runs on PRs and blocks Pages deployment before publication. Dependencies are locked; Dependabot proposes weekly npm and action updates. Browser screenshots/traces are retained on failures. There are no pixel-baseline comparisons yet, and passing checks is not a guarantee against every visual or security defect.

## Primary documentation

- [React in an existing project](https://react.dev/learn/add-react-to-an-existing-project)
- [Playwright CI](https://playwright.dev/docs/ci-intro)
- [RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html) / [Cloud SQL PostgreSQL](https://cloud.google.com/sql/docs/postgres/introduction)
- [ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html) / [Memorystore](https://cloud.google.com/memorystore/docs/redis/redis-overview)
- [S3 object storage](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [Cloud Run](https://cloud.google.com/run/docs/overview/what-is-cloud-run)
