# Example Project-Specific Rules

Copy and adapt these rules to your `.codex/prompts/controller.md` file.

---

## Web Application Example

```markdown
## Project-Specific Rules

### Repository Structure
- Frontend: `frontend/` (React/TypeScript)
- Backend: `backend/` (Python/FastAPI)
- Infrastructure: `infra/` (Terraform)
- Shared types: `shared/`

### CI/CD Requirements
- All PRs require:
  - Passing unit tests (>= 80% coverage)
  - Passing integration tests
  - Linting (ESLint, Black, Ruff)
  - Type checking (TypeScript strict, mypy)
- Deploy to staging on PR merge to `develop`
- Deploy to production on release tag

### Security Policies
- Authentication via OAuth2/OIDC only
- All API endpoints require authentication except `/health`
- Use parameterized queries (no raw SQL)
- Secrets in environment variables or secret manager
- HTTPS required for all external communication

### Database Rules
- Migrations must be reversible
- No direct production database access
- Use connection pooling
- Index all foreign keys

### Code Style
- Follow existing patterns in the codebase
- Prefer composition over inheritance
- Use dependency injection
- Write docstrings for public APIs
```

---

## Infrastructure/DevOps Example

```markdown
## Project-Specific Rules

### Repository Structure
- Modules: `modules/` (reusable Terraform)
- Environments: `environments/{dev,staging,prod}/`
- Scripts: `scripts/`
- Documentation: `docs/`

### Infrastructure Principles
- Infrastructure as Code only (no manual changes)
- All changes via PR with plan output
- State stored in remote backend (S3/GCS)
- State locking enabled

### Security Policies
- Least privilege IAM
- No wildcard permissions
- VPC isolation for sensitive workloads
- Encryption at rest and in transit
- Audit logging enabled

### Change Management
- Changes to production require:
  - Approved PR
  - Passing plan validation
  - No security warnings
  - Scheduled maintenance window (if breaking)

### Cost Management
- Tag all resources with: team, environment, project
- Use spot/preemptible instances where appropriate
- Set up billing alerts
- Review cost reports weekly
```

---

## Data Pipeline Example

```markdown
## Project-Specific Rules

### Repository Structure
- Pipelines: `pipelines/`
- Transformations: `transforms/`
- Tests: `tests/`
- Schemas: `schemas/`

### Data Quality
- All pipelines must have:
  - Input validation
  - Output schema verification
  - Data quality checks (nulls, duplicates, ranges)
  - Idempotent processing

### Security & Privacy
- PII must be:
  - Encrypted in transit and at rest
  - Masked in logs
  - Retained per policy (delete after N days)
- Access logged and auditable

### Pipeline Design
- Prefer batch over streaming unless latency required
- Use checkpointing for recovery
- Implement backfill capability
- Document data lineage

### Testing Requirements
- Unit tests for all transformations
- Integration tests with sample data
- Data quality tests in production (monitoring)
```

---

## Mobile App Example

```markdown
## Project-Specific Rules

### Repository Structure
- iOS: `ios/` (Swift)
- Android: `android/` (Kotlin)
- Shared: `shared/` (KMM or shared logic)
- Backend: `backend/`

### Release Process
- Beta releases to TestFlight/Play Console
- Production releases require:
  - QA sign-off
  - Crash-free rate > 99.5%
  - No P0/P1 bugs
  - App store compliance check

### Security Policies
- Certificate pinning required
- Secure storage for tokens (Keychain/Keystore)
- No sensitive data in logs
- Biometric auth for sensitive operations

### Performance Requirements
- Cold start < 2 seconds
- Frame rate >= 60 fps
- Memory usage < 200MB
- Battery impact monitored

### Accessibility
- VoiceOver/TalkBack support required
- Minimum touch target 44x44 points
- Color contrast ratios met
- Dynamic type support
```

---

## Usage

1. Copy the relevant section to your controller prompt
2. Customize for your specific project
3. Add/remove rules as needed
4. Test with the controller to ensure rules are followed
