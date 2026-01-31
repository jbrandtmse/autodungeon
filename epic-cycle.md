# Epic Development Cycle Slash Command

Develop a slash command that executes the BMAD Method development cycle sequentially for all stories in an Epic. The task sequence is:

1. `/bmad-bmm-create-story`
2. `/bmad-bmm-dev-story`
3. `/bmad-bmm-code-review`
4. Commit and Push to Git
5. `/bmad-bmm-testarch-automate`
6. Commit and Push to Git

Make sure to include a file for the slash command in the `/.claude/commands` folder so the workflow can be executed as a slash command.

## Execution Guidelines

**IMPORTANT:** Each task should be executed as a sub-agent.

Automatically resolve all high and medium severity issues found during code review using your best judgment and BMAD guidance.

## When to Pause

Within each sub-agent, only pause to ask me a question if:

- The acceptance criteria or requirements are ambiguous
- There are multiple reasonable design options and my preference matters
- Proceeding would risk breaking important constraints (security, compliance, performance, interoperability)

## Handling Clarifications

When you need clarification, do not continue autonomously for that story. Instead:

- Surface a clear, numbered question back to me in the main conversation
- Include a concise summary of the relevant context (Story ID, file(s) affected, key tradeoffs)
- Wait for my answer before resuming work on that story's sub-agent

After I answer, incorporate my response as a hard constraint and resume the same story's sub-agent workflow from where it left off. Continue through the task sequence as needed.

## Completion Logging

At the completion of each story, write a brief log entry summarizing:

- Story ID/name
- Files touched
- Key design decisions
- Any issues auto-resolved vs. those that required my input
