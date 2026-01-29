---
title: 'Epic Development Cycle Definition of Done Checklist'
validation-target: 'Epic cycle execution and story completion'
validation-criticality: 'HIGHEST'
required-inputs:
  - 'Sprint status file (sprint-status.yaml)'
  - 'Epic number or auto-discovery'
optional-inputs:
  - 'Specific story override'
validation-rules:
  - 'All stories in epic must be processed through complete cycle'
  - 'All HIGH and MEDIUM severity issues must be auto-resolved'
  - 'Git commits must be pushed for each story'
  - 'Cycle log must be written with complete summary'
---

# Epic Development Cycle Definition of Done Checklist

## 1. Pre-Cycle Validation

### 1.1 Epic Discovery
- [ ] **Epic Identified:** Target epic number is determined (provided or auto-discovered)
- [ ] **Sprint Status Loaded:** sprint-status.yaml is read and parsed completely
- [ ] **Story Queue Built:** All stories for the epic are identified and queued in order

### 1.2 Environment Ready
- [ ] **Git Clean State:** Working directory is clean or changes are stashed
- [ ] **Branch Correct:** On appropriate branch for development
- [ ] **Cycle Log Initialized:** epic-dev-cycle-log.md created/appended

## 2. Per-Story Cycle Validation

### 2.1 Create Story Phase (if status = backlog)
- [ ] **Sub-Agent Launched:** create-story workflow executed via Task tool
- [ ] **Story File Created:** Story markdown file exists in implementation-artifacts
- [ ] **Dev Notes Complete:** Story contains comprehensive implementation guidance
- [ ] **Status Updated:** Sprint status shows ready-for-dev for this story

### 2.2 Dev Story Phase
- [ ] **Sub-Agent Launched:** dev-story workflow executed via Task tool
- [ ] **All Tasks Complete:** Every task/subtask in story file is marked [x]
- [ ] **Tests Written:** Unit tests exist for implemented functionality
- [ ] **Tests Pass:** All tests pass (new and regression)
- [ ] **File List Updated:** Story file contains complete list of changed files
- [ ] **Status Updated:** Sprint status shows review for this story

### 2.3 Code Review Phase
- [ ] **Sub-Agent Launched:** code-review workflow executed via Task tool
- [ ] **Issues Found:** 3-10 issues identified per BMAD code-review requirements
- [ ] **HIGH Issues Auto-Resolved:** All HIGH severity issues fixed automatically
- [ ] **MEDIUM Issues Auto-Resolved:** All MEDIUM severity issues fixed automatically
- [ ] **LOW Issues Documented:** LOW severity issues logged but not blocking
- [ ] **Tests Still Pass:** Fixes did not break existing tests
- [ ] **Review Section Updated:** Story file contains review findings and resolutions

### 2.4 Post-Review Commit Phase
- [ ] **Changes Staged:** All implementation and story files staged
- [ ] **Commit Message Proper:** Follows conventional commit format with story ID
- [ ] **Co-Author Added:** Claude Opus 4.5 attribution included
- [ ] **Push Successful:** Changes pushed to remote repository

### 2.5 Test Automation Phase
- [ ] **Sub-Agent Launched:** testarch-automate workflow executed via Task tool
- [ ] **Coverage Analyzed:** Test gaps identified for story files
- [ ] **Tests Generated:** Additional tests created where needed
- [ ] **Tests Pass:** All generated tests pass

### 2.6 Final Commit Phase
- [ ] **Test Files Staged:** New test files added to git
- [ ] **Commit Created:** Test commit with proper message
- [ ] **Push Successful:** Test changes pushed to remote
- [ ] **Story Status Done:** Sprint status updated to done for this story

### 2.7 Story Log Entry
- [ ] **Log Entry Written:** Cycle log contains entry for this story with:
  - Story ID/name
  - Files touched (complete list)
  - Key design decisions made
  - Issues auto-resolved (with descriptions)
  - User input required (if any, with questions and answers)

## 3. Autonomy Compliance

### 3.1 Auto-Resolution Rules
- [ ] **HIGH Severity Auto-Fixed:** All HIGH issues resolved without user intervention
- [ ] **MEDIUM Severity Auto-Fixed:** All MEDIUM issues resolved without user intervention
- [ ] **BMAD Guidance Applied:** Fixes follow BMAD best practices

### 3.2 Pause Conditions Respected
- [ ] **Ambiguous Requirements:** Paused only when requirements genuinely unclear
- [ ] **Design Options:** Paused only when multiple valid approaches with real tradeoffs
- [ ] **Risk Constraints:** Paused only when security/compliance/performance at risk
- [ ] **No Unnecessary Pauses:** Did not pause for resolvable issues

### 3.3 Question Format (When Paused)
- [ ] **Numbered Question:** Clear, numbered question provided
- [ ] **Context Included:** Story ID, files affected, key tradeoffs summarized
- [ ] **User Answer Incorporated:** Response treated as hard constraint
- [ ] **Workflow Resumed:** Continued from pause point correctly

## 4. Epic Completion Validation

### 4.1 All Stories Processed
- [ ] **Queue Exhausted:** Every story in the epic queue was processed
- [ ] **All Stories Done:** Sprint status shows done for all epic stories
- [ ] **Epic Status Updated:** Epic marked as done (if all stories complete)

### 4.2 Final Cycle Log
- [ ] **Summary Written:** Epic completion summary in cycle log
- [ ] **Statistics Complete:** Totals for files, decisions, auto-resolved, user input
- [ ] **Recommendations Provided:** Next steps suggested

## 5. Quality Gates

### 5.1 Test Coverage
- [ ] **No Test Regressions:** All pre-existing tests still pass
- [ ] **New Tests Pass:** All tests written during cycle pass
- [ ] **Coverage Maintained:** Test coverage not decreased

### 5.2 Code Quality
- [ ] **Linting Passes:** No new lint errors introduced
- [ ] **Type Checking Passes:** No new type errors (if applicable)
- [ ] **Security Review:** No obvious security issues introduced

### 5.3 Documentation
- [ ] **Story Files Complete:** All story files properly updated
- [ ] **Cycle Log Complete:** Full audit trail of work performed
- [ ] **Sprint Status Accurate:** Reflects true state of all stories

## Validation Failure Actions

If any validation fails:

1. **Pre-Cycle Failure:** HALT and report missing prerequisites
2. **Per-Story Phase Failure:** Attempt recovery; if unrecoverable, pause and surface to user
3. **Auto-Resolution Failure:** Log issue and attempt alternative fix; escalate if unable
4. **Push Failure:** Retry once; if persistent, pause and await user guidance
5. **Epic Completion Failure:** Document incomplete state in cycle log
