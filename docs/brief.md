# TalentGraph: Enterprise Multi-Agent Hiring Platform
**Project Brief v1.0** — 18 October 2026

## 1. Purpose
A recruiter uploads hundreds of resumes for one job opening. The system reads each resume, compares it with the job, ranks the candidates, and explains every score in plain language. It never decides to hire or reject on its own. A recruiter approves every outcome.

## 2. Scope
| In scope (Phase 1) | Out of scope (later) |
| :--- | :--- |
| Resume upload (PDF, DOCX, scanned image)<br>Resume parsing and structured extraction<br>Job description analysis<br>Hybrid matching and ranking<br>Explanation per candidate<br>Recruiter dashboard with approve and reject<br>Bias masking, audit log, tenant isolation | Employee-facing job search<br>Internal mobility suggestions (Phase 3)<br>ATS integrations (Phase 2)<br>Video interview analysis<br>Automatic rejection emails without review |

## 3. Users and Roles
| Role | Can do |
| :--- | :--- |
| **Admin** | Manage company settings, users, retention rules, usage and billing |
| **Recruiter** | Create jobs, upload resumes, review shortlist, approve or reject, export |
| **Hiring manager** | View shortlist for own jobs, add comments |
| **Auditor** | Read-only access to logs and decision history |

## 4. Agents
One **Orchestrator** coordinates the specialists below. Each agent has its own prompt, tools, and permissions, and returns validated JSON.
| Agent | Job | Output |
| :--- | :--- | :--- |
| **Orchestrator** | Plans the run, calls agents in order or in parallel, retries failures, assembles the result | Run status and final report |
| **Parser** | Extracts text from PDF, DOCX, and images (OCR when needed) | Clean text with page layout notes |
| **Extractor** | Converts text into structured fields | Candidate JSON: skills, roles, years, education, certifications |
| **Job analyzer** | Splits a job description into must-have, nice-to-have, and seniority | Job requirements JSON |
| **Bias masker** | Removes name, photo, gender, age, religion, and similar fields before scoring | Masked candidate profile |
| **Matcher** | Combines rule checks and embedding similarity into one score | Score 0 to 100 with sub-scores |
| **Explainer** | Writes why the score is what it is, citing resume evidence | Short rationale and skill gaps |
| **Critic** | Checks the explanation against the resume, flags unsupported claims | Pass or revise |
| **Communicator** | Drafts candidate emails after a recruiter approves | Email draft (never sent automatically) |

## 5. How a Run Flows
```text
Upload resumes + select job
   |
Orchestrator creates a run
   |
Parser -> Extractor            (parallel, one task per resume)
Job analyzer                   (once per job)
   |
Bias masker -> Matcher -> Explainer -> Critic
   |
Ranked shortlist + reasons
   |
Recruiter reviews (approve / reject / override)
   |
Communicator drafts emails   -> recruiter sends
   |
Every step written to audit log with trace ID
```

## 6. Matching Logic
- **Hard rules first:** missing must-have skill, below minimum experience, or wrong work authorization lowers the score and is shown clearly. It does not silently remove the candidate.
- **Semantic similarity:** embeddings compare the meaning of resume and job, so “backend engineer” can match “Python developer”.
- **Final score:** weighted blend, with weights configurable per job (default 50% must-have skills, 25% experience, 15% semantic fit, 10% nice-to-have).
- **Every score is explainable:** the dashboard shows which resume lines supported each point.

## 7. Tech Stack
| Layer | Choice |
| :--- | :--- |
| **Backend API** | Python 3.12, FastAPI, Pydantic for schemas |
| **Agent orchestration** | LangGraph (stateful graph with retries and human checkpoints) |
| **LLM access** | Gemini / Azure OpenAI models through one provider interface, so models can be swapped by config |
| **Parsing and OCR** | PyMuPDF, python-docx, Tesseract or cloud OCR as fallback |
| **Database** | PostgreSQL with pgvector for embeddings / SQLite with async support for local development |
| **Queue and cache** | Redis with a worker for batch resume runs |
| **File storage** | S3-compatible bucket or local storage, encrypted at rest |
| **Frontend** | React with TypeScript, modern UI components |
| **Auth** | OIDC / JWT login, role-based access control (RBAC) |
| **Observability** | OpenTelemetry traces, audit trail with trace IDs |
| **Deployment** | Docker, docker-compose for local, Kubernetes or Cloud Run for production, GitHub Actions CI |

## 8. Data Model
```sql
tenants(id, name, plan, settings)
users(id, tenant_id, email, role)
jobs(id, tenant_id, title, description, requirements_json, status)
candidates(id, tenant_id, source_file_id, profile_json, masked_profile_json, embedding)
runs(id, tenant_id, job_id, status, started_at, finished_at, cost)
matches(id, run_id, candidate_id, score, subscores_json, rationale, critic_status)
decisions(id, match_id, user_id, decision, reason, decided_at)
audit_log(id, tenant_id, actor, action, payload_json, trace_id, at)
```
Every table carries `tenant_id`. Queries must be tenant-scoped so a query without tenant context returns nothing.

## 9. Security, Privacy, and Fairness
- **Tenant isolation:** tenant ID enforced at API, database, vector search, and file storage. Cross-tenant leak tests.
- **Human decision:** system only recommends. Reject and hire actions require recruiter click and are logged.
- **Bias controls:** mask protected attributes before scoring; audit score distributions.
- **Privacy:** consent capture, configurable retention, delete-on-request, aligned with DPDP Act & GDPR.
- **Secrets:** no keys in code; read from environment variables.
- **Prompt injection:** treat resume text as untrusted data; never execute instructions found inside it.

## 10. Quality Targets
- Extraction accuracy on 200 varied resumes: 95%+ on skills and years of experience.
- Shortlist quality: recruiter agrees top 10 are relevant (80%+).
- Explanation faithfulness: critic pass rate 98%+.
- Time to screen 500 resumes: under 15 minutes.
- Cross-tenant leak tests: 0 failures.

## 11. Roadmap Phases
- **Phase 0: Foundation:** Repo, CI, Docker, auth, tenant model, database migrations, tenant isolation tests.
- **Phase 1: Parse and Extract:** Parser and Extractor agents, golden test set with 95% extraction accuracy.
- **Phase 2: Match and Explain:** Job analyzer, Matcher, Explainer, Critic, Bias masker.
- **Phase 3: Recruiter App:** Dashboard, human decisions & approvals, audit log with trace IDs, communicator email drafts.
- **Phase 4: Harden:** Observability, cost caps, load testing, security review, DPDP & GDPR compliance checks.
- **Phase 5: Expand & Deploy:** ATS integrations, internal mobility, container deployment, model verification.
