---
description: 'Orchestrates complete BMAD development cycle for all stories in an Epic: create-story -> dev-story -> code-review -> commit/push -> testarch-automate -> commit/push. Auto-resolves HIGH/MEDIUM issues, only pauses for ambiguous requirements or critical decisions.'
---

IT IS CRITICAL THAT YOU FOLLOW THESE STEPS - while staying in character as the current agent persona you may have loaded:

<steps CRITICAL="TRUE">
1. Always LOAD the FULL @_bmad/core/tasks/workflow.xml
2. READ its entire contents - this is the CORE OS for EXECUTING the specific workflow-config @_bmad/bmm/workflows/4-implementation/epic-dev-cycle/workflow.yaml
3. Pass the yaml path _bmad/bmm/workflows/4-implementation/epic-dev-cycle/workflow.yaml as 'workflow-config' parameter to the workflow.xml instructions
4. Follow workflow.xml instructions EXACTLY as written to process and follow the specific workflow config and its instructions
5. Execute each sub-workflow (create-story, dev-story, code-review, testarch-automate) as a SUB-AGENT using the Task tool
6. Auto-resolve ALL HIGH and MEDIUM severity issues from code-review using your best judgment and BMAD guidance
7. ONLY pause to surface questions when:
   - Acceptance criteria or requirements are genuinely AMBIGUOUS
   - Multiple reasonable design options exist where user preference matters
   - Proceeding would risk security, compliance, performance, or interoperability
8. When pausing, format questions as:
   - Clear numbered question
   - Context summary (Story ID, files affected, key tradeoffs)
   - Then WAIT for user answer
9. After user answers, incorporate response as HARD CONSTRAINT and resume from pause point
10. After each story completes, write log entry summarizing:
    - Story ID/name
    - Files touched
    - Key design decisions
    - Issues auto-resolved vs those requiring user input
</steps>

<autonomy-rules>
## Sub-Agent Execution
Each phase of the development cycle MUST be executed as a sub-agent via the Task tool:
- `/bmad-bmm-create-story` - Create story from epic backlog
- `/bmad-bmm-dev-story` - Implement story tasks
- `/bmad-bmm-code-review` - Adversarial code review
- `/bmad-bmm-testarch-automate` - Expand test coverage

## Auto-Resolution Policy
- HIGH severity issues: AUTO-FIX immediately using best judgment
- MEDIUM severity issues: AUTO-FIX using BMAD best practices
- LOW severity issues: Document only, do not require user input

## Pause Conditions (ONLY pause for these)
1. **Ambiguous Requirements** - Cannot reasonably infer intent
2. **Design Options** - Multiple valid approaches with significant user-preference implications
3. **Risk Constraints** - Security, compliance, performance, or interoperability at risk

## Question Format (When Paused)
```
**User Input Required - Story {story_key}**

{numbered_question}

**Context:**
- Story: {story_id}
- Phase: {current_phase}
- Files: {affected_files}
- Tradeoffs: {key_tradeoffs}
```
</autonomy-rules>

<cycle-sequence>
## Per-Story Cycle
1. **Create Story** (if backlog) -> status becomes ready-for-dev
2. **Dev Story** -> implements all tasks -> status becomes review
3. **Code Review** -> finds/fixes issues -> auto-resolves HIGH/MEDIUM
4. **Git Commit & Push** -> commits implementation + review fixes
5. **Test Automation** -> expands test coverage
6. **Git Commit & Push** -> commits new tests -> status becomes done
7. **Log Entry** -> writes summary to cycle log
8. **Next Story** -> continues with next story in queue
</cycle-sequence>
