---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md
---

# macs_dev - Epic Breakdown: Guided Onboarding

## Overview

This document provides the complete epic and story breakdown for the MACS guided onboarding initiative. It decomposes the initiative-specific PRD, UX design, and architecture into implementable stories that stay grounded in the current `macs setup` surface, current docs, and current regression seams.

## Requirements Inventory

### Functional Requirements

FR1: Operators can launch guided onboarding from the existing `macs setup` surface.  
FR2: Operators can receive a concise explanation of the controller-owned MACS model before or during onboarding.  
FR3: Operators can see the current repo onboarding state at the start of the guided flow.  
FR4: Operators can understand whether the current step is read-only guidance or a state-changing command.  
FR5: The system can inspect repo-local bootstrap, configuration, runtime availability, worker registration, and worker readiness using current controller-owned sources.  
FR6: The system can classify onboarding state as blocked, partial, pass, or equivalent controller-recognized readiness states.  
FR7: The system can recommend the next safe operator action based on the current repo state.  
FR8: The system can explain why a recommended next action matters and what condition it is intended to resolve.  
FR9: Operators can distinguish auto-detected facts from actions that require explicit operator execution or confirmation.  
FR10: Operators can follow the conservative onboarding order already established by MACS setup guidance.  
FR11: Operators can understand why runtime availability alone does not establish safe-ready-state.  
FR12: Operators can review readiness gaps by adapter, runtime availability, worker registration, and ready-state evidence.  
FR13: Operators can understand the boundary between bridge-era workflows and controller-owned setup workflows.  
FR14: Operators can tell whether a repo is initialized, configured, partially ready, or safe-ready without inspecting raw state files directly.  
FR15: Operators can inspect the specific reasons behind a blocked or partial onboarding result.  
FR16: The system can recommend targeted remediation paths for common onboarding failure modes.  
FR17: Operators can access intervention and recovery guidance relevant to onboarding-related readiness problems.  
FR18: Operators can inspect or reference the underlying controller evidence that supports a guidance recommendation.  
FR19: Operators can move from guided output to the relevant canonical documentation for deeper explanation.  
FR20: The system can present current, canonical example commands for the onboarding step being discussed.  
FR21: Maintainers can keep onboarding guidance aligned with README and docs without creating a second authoritative product model.  
FR22: Operators can use guided onboarding successfully in narrow terminals and no-color terminal environments.  
FR23: Operators can interpret warnings, degraded states, and next-step guidance without relying on color alone.  
FR24: Operators can request machine-readable onboarding and readiness signals through stable structured output modes where automation or evidence capture is needed.  
FR25: Guided onboarding can provide direction without auto-installing runtimes or auto-registering workers.  
FR26: Guided onboarding can preserve operator-confirmed behavior for any state-changing actions it references.  
FR27: Guided onboarding can preserve controller authority and avoid introducing shadow state, hidden side effects, or alternate readiness engines.  
FR28: Maintainers can regression-test onboarding behavior through existing setup-family test and documentation surfaces.  
FR29: Contributors can update onboarding flow and copy without changing canonical command grammar unless the underlying contract changes.  
FR30: Planning, UX, and architecture work for guided onboarding can trace back to this PRD without redefining the broader MACS product scope.

### NonFunctional Requirements

NFR1: Read-only guided onboarding state inspection shall complete within 2 seconds for a typical local repo with initialized controller state and no live worker mutations in progress.  
NFR2: Full readiness interpretation that reuses existing setup validation data shall complete within 5 seconds for the current repo-local adapter set under normal local conditions.  
NFR3: Guided onboarding shall never report a readiness state higher than the result supported by the underlying controller-owned setup and validation surfaces for the same repo state.  
NFR4: Any guided path that references a state-changing action shall preserve existing explicit confirmation requirements and safe-state transitions defined by the MACS control plane.  
NFR5: When guidance depends on incomplete, stale, degraded, or unavailable evidence, the affected output shall label that uncertainty explicitly before recommending the next action.  
NFR6: Human-readable onboarding output must remain usable at 80 columns and in half-width tmux panes.  
NFR7: No-color mode shall retain full semantic clarity through textual state labels, warning labels, and structural formatting alone.  
NFR8: Onboarding output pasted into plain-text issues, docs, or chat shall remain understandable without terminal styling or hidden context.  
NFR9: Guided onboarding terminology shall match canonical MACS object and command vocabulary across CLI output, docs, UX artifacts, and stories.  
NFR10: All onboarding examples and recommended commands shall match the documented canonical command forms in the maintained docs set at release time.  
NFR11: Changes to onboarding behavior shall be traceable through planning artifacts, docs updates, and regression coverage rather than through copy-only changes.  
NFR12: Automated regression coverage shall exercise at least blocked, partial, and pass onboarding/readiness scenarios through the existing setup-family test seams.  
NFR13: The onboarding design shall reuse current setup/readiness read models and documentation sources wherever practical so that readiness logic is defined in one place.

### Additional Requirements

- Add the guided experience under the existing setup-family CLI as `macs setup guide` with human-readable and `--json` modes.  
- Compose the guide from current setup snapshot, dry-run, validation, and compatibility guidance rather than creating a new readiness engine.  
- Keep onboarding strictly read-only and avoid introducing new control-plane state, config files, or persistence.  
- Keep the output order stable: orientation, current state, gaps, next action, related commands, docs.  
- Centralize doc-reference mapping so human-readable and JSON outputs point to the same canonical docs.  
- Extend the current setup-family regression seam in `tools/orchestration/tests/test_setup_init.py` instead of creating a new test module.  
- Update the canonical docs set together with guide behavior so operator examples do not drift.

### UX Design Requirements

UX-DR1: Provide an Orientation Brief that explains controller-owned truth and why runtime availability is only a hint.  
UX-DR2: Provide a Setup State Summary showing outcome, safe-ready-state, enabled adapters, and worker counts.  
UX-DR3: Provide a Conservative Step Ladder that reflects the existing onboarding order and labels read-only versus action steps.  
UX-DR4: Provide a Gap Explanation List that groups readiness issues by gap type and provenance.  
UX-DR5: Provide a Next Action Card with one primary recommendation and a one-line reason.  
UX-DR6: Provide a Migration Summary block for supported unchanged helpers versus controller-owned normal flows.  
UX-DR7: Keep the human-readable guide usable in narrow terminals and `NO_COLOR` mode without losing meaning.  
UX-DR8: Provide stable JSON parity for the same guidance content where automation or evidence capture needs it.  
UX-DR9: Provide an Evidence and Doc Reference block so support and advanced users can trace the guide back to controller facts and canonical docs.

### FR Coverage Map

FR1: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR2: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR3: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR4: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR5: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR6: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR7: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR8: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR9: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR10: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR11: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR12: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR13: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR14: Epic 1 - Start Guided Onboarding from the Existing Setup Surface  
FR15: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR16: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR17: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR18: Epic 2 - Turn Partial and Blocked States into Exact Remediation  
FR19: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR20: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR21: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR22: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR23: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR24: Epic 3 - Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation  
FR25: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time  
FR26: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time  
FR27: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time  
FR28: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time  
FR29: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time  
FR30: Epic 4 - Preserve Authoritative Onboarding Behavior Over Time

## Epic List

### Epic 1: Start Guided Onboarding from the Existing Setup Surface

Operators can launch a controller-owned onboarding guide from `macs setup` and immediately understand current repo state, readiness outcome, and the conservative setup order without inspecting raw files.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR9, FR10, FR11, FR14

### Epic 2: Turn Partial and Blocked States into Exact Remediation

Operators can turn onboarding gaps into clear, evidence-backed next actions, including migration and recovery-oriented follow-up guidance, without reverse-engineering raw validation output.

**FRs covered:** FR7, FR8, FR12, FR13, FR15, FR16, FR17, FR18

### Epic 3: Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation

Operators and maintainers can use the guided onboarding experience consistently across docs, narrow terminal conditions, and structured local automation flows.

**FRs covered:** FR19, FR20, FR21, FR22, FR23, FR24

### Epic 4: Preserve Authoritative Onboarding Behavior Over Time

Maintainers and contributors can evolve the onboarding guide without weakening safety, contract truth, or planning traceability.

**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30

## Epic 1: Start Guided Onboarding from the Existing Setup Surface

Operators can launch a controller-owned onboarding guide from `macs setup` and immediately understand current repo state, readiness outcome, and the conservative setup order without inspecting raw files.

### Story 1.1: Add a guided onboarding entry point

As a technical adopter,  
I want a guided onboarding command under `macs setup`,  
So that I can start from the canonical MACS setup surface instead of piecing together several commands manually.

**Requirements:** FR1, FR4, FR9; NFR3, NFR9, NFR13

**Acceptance Criteria:**

**Given** the current MACS CLI is installed in the repo  
**When** I run `macs setup guide` or `macs setup guide --json`  
**Then** the command resolves through the existing setup-family parser and returns a read-only onboarding briefing  
**And** the output makes it explicit which recommended commands are read-only versus state-changing follow-ups

### Story 1.2: Summarize controller-owned onboarding state

As an operator,  
I want the guide to summarize the repo’s actual onboarding state,  
So that I can tell whether the repo is initialized, configured, partially ready, or safe-ready without inspecting raw state directly.

**Requirements:** FR3, FR5, FR6, FR14; NFR1, NFR2, NFR3; UX-DR2

**Acceptance Criteria:**

**Given** a repo with any combination of bootstrap, configuration, runtime, and worker state  
**When** I run `macs setup guide`  
**Then** the guide reports the current readiness outcome using the same controller-supported semantics as setup validation  
**And** the summary includes the minimum state facts needed to explain that result, including enabled adapters and worker counts

### Story 1.3: Present the controller model and conservative order

As a new MACS adopter,  
I want the guide to explain the controller-owned model and conservative onboarding order,  
So that I understand why runtime binaries alone are not enough and what sequence MACS expects me to follow.

**Requirements:** FR2, FR10, FR11; NFR8, NFR10; UX-DR1, UX-DR3

**Acceptance Criteria:**

**Given** I am unfamiliar with the MACS setup model  
**When** I run the guide from any repo state  
**Then** the output includes a concise explanation of controller-owned truth and the conservative setup order already exposed by MACS  
**And** the explanation explicitly states that runtime presence on `PATH` does not by itself establish safe-ready-state

## Epic 2: Turn Partial and Blocked States into Exact Remediation

Operators can turn onboarding gaps into clear, evidence-backed next actions, including migration and recovery-oriented follow-up guidance, without reverse-engineering raw validation output.

### Story 2.1: Explain blocked and partial gaps with provenance

As an operator,  
I want blocked and partial onboarding gaps broken out by cause and evidence source,  
So that I can understand what is actually wrong instead of inferring from a flat list of issues.

**Requirements:** FR12, FR15, FR18; NFR3, NFR5; UX-DR4, UX-DR9

**Acceptance Criteria:**

**Given** a repo in a blocked or partial onboarding state  
**When** I run the guide  
**Then** the guide groups gaps by meaningful categories such as bootstrap, runtime availability, registration, and ready-worker evidence  
**And** each gap makes clear whether it comes from controller facts, runtime hints, or guide interpretation

### Story 2.2: Recommend the next safe onboarding action

As an operator,  
I want one prioritized next action with a reason,  
So that I know what to do next without guessing which command matters most.

**Requirements:** FR7, FR8, FR16; NFR4, NFR5; UX-DR5

**Acceptance Criteria:**

**Given** the guide has identified the current onboarding state and active gaps  
**When** it renders the response  
**Then** it presents one primary next action tied to the highest-priority unresolved condition  
**And** the recommendation explains what condition the command is expected to resolve before listing any secondary follow-ups

### Story 2.3: Surface migration and recovery follow-ups

As an existing MACS user,  
I want the guide to distinguish supported unchanged helpers from controller-owned setup and recovery flows,  
So that I can migrate safely without mixing legacy habits with normal control-plane operations.

**Requirements:** FR13, FR17; NFR9, NFR10; UX-DR6

**Acceptance Criteria:**

**Given** the repo still exposes bridge-era helpers and compatibility paths  
**When** I run the guide  
**Then** the response includes a migration summary identifying what remains supported unchanged and what is now superseded for normal orchestration work  
**And** onboarding-related recovery guidance points to the relevant `task` or `recovery` follow-up commands without implying hidden automation

## Epic 3: Keep Guided Onboarding Canonical Across Docs, Terminals, and Automation

Operators and maintainers can use the guided onboarding experience consistently across docs, narrow terminal conditions, and structured local automation flows.

### Story 3.1: Link guided output to canonical docs and examples

As an operator,  
I want guided onboarding to point me to the right docs and current example commands,  
So that I can go deeper without the guide becoming a second authoritative documentation surface.

**Requirements:** FR19, FR20, FR21; NFR10, NFR11; UX-DR9

**Acceptance Criteria:**

**Given** the guide discusses a specific onboarding concept or next step  
**When** it renders docs and command references  
**Then** it points to the canonical maintained docs and uses the same command forms those docs publish  
**And** the docs set is updated wherever needed so the guide and documentation describe the same onboarding model

### Story 3.2: Render guided onboarding for narrow and no-color terminals

As an operator working in tmux or plain text environments,  
I want the guide to stay understandable without wide layouts or color,  
So that terminal constraints do not hide meaning or next steps.

**Requirements:** FR22, FR23; NFR6, NFR7, NFR8; UX-DR7

**Acceptance Criteria:**

**Given** I run the guide in an 80-column or `NO_COLOR=1` environment  
**When** the command renders human-readable output  
**Then** all critical meaning remains visible through textual labels, ordering, and structure alone  
**And** no essential warning, readiness state, or next action depends on color or wide-screen formatting

### Story 3.3: Provide stable JSON guidance output

As an automation-oriented operator or maintainer,  
I want the same onboarding guidance available in a stable structured envelope,  
So that I can script local checks or capture support evidence without scraping human-readable text.

**Requirements:** FR24; NFR9, NFR13; UX-DR8

**Acceptance Criteria:**

**Given** I run `macs setup guide --json`  
**When** the command returns onboarding guidance  
**Then** the JSON includes the same essential sections as the human-readable flow, including outcome, state summary, gaps, next actions, and doc references  
**And** the structured output remains suitable for regression assertions and evidence capture

## Epic 4: Preserve Authoritative Onboarding Behavior Over Time

Maintainers and contributors can evolve the onboarding guide without weakening safety, contract truth, or planning traceability.

### Story 4.1: Preserve read-only boundaries in guided onboarding

As a maintainer,  
I want the guide to remain read-only and controller-truth-first,  
So that onboarding help never becomes hidden setup automation or a shadow readiness engine.

**Requirements:** FR25, FR26, FR27; NFR3, NFR4, NFR13

**Acceptance Criteria:**

**Given** the guide references commands that can change controller state  
**When** it recommends those commands  
**Then** it presents them only as explicit operator actions and does not execute them implicitly  
**And** the guide never reports a readiness state more optimistic than the underlying setup-family read model supports

### Story 4.2: Regression-cover blocked, partial, and pass guide states

As a maintainer,  
I want the guide covered by the existing setup-family regression surface,  
So that onboarding behavior stays aligned with implemented controller facts as the repo evolves.

**Requirements:** FR28; NFR12, NFR13

**Acceptance Criteria:**

**Given** setup-family regression tests run in CI or local development  
**When** guide behavior is exercised across blocked, partial, and pass scenarios  
**Then** the tests assert the expected readiness classification, gap interpretation, and primary next-action behavior  
**And** the coverage extends the existing setup-family test seams instead of introducing a disconnected onboarding-only harness

### Story 4.3: Publish contributor maintenance guidance for onboarding parity

As a contributor,  
I want clear maintenance expectations for guide copy, docs, and planning traceability,  
So that I can update onboarding safely without drifting from canonical command grammar or the initiative scope.

**Requirements:** FR29, FR30; NFR10, NFR11

**Acceptance Criteria:**

**Given** a contributor changes onboarding behavior or wording  
**When** they prepare the change for review  
**Then** the contributor-facing guidance identifies which docs, tests, and planning artifacts must stay in sync  
**And** the resulting change can be traced back to this initiative-specific PRD, UX spec, and architecture rather than redefining the broader MACS product scope
