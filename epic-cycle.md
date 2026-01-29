Develope a slash command that executes the BMAD Method developement cycle in order sequentially for all of the stories in an Epic.  The task sequence is /bmad-bmm-create-story; /bmad-bmm-dev-story ; /bmad-bmm-code-review; Commit and Push to Git; /bmad-bmm-testarch-automate ; Commit and Push to Git.  Make sure your include a file for the slash command in the /.claude/commands folder so the workflow can be executed as a slash command.
IMPORTANT: Each task should be executed as a sub-agent.   
Automatically resolve all high and medium severity issues found during code review using your best judgement and BMAD guidance.
Within each subagent only pause to ask me a question if:
- The acceptance criteria or requirements are ambigous
- There are multiple reasonable design options and my preference maters, or
- Proceeding would risk breaking important contstraints (security, compliance, performance, interoperability)
When you need oeprating, do not continue autonmously for that story.  Instead:
- Surface a clear, numbered question back to me in the main conversation
- Include a concise summary of the relavant context (Story ID, file(s) affected, key tradeoffs)
- Wait for my ansewr before resuming work on that story's sub-agent
After I anser, incorportate my response as a hard contrant and resume the same story's sub-agent workflow from where it left off, continue through  /bmad-bmm-create-story; /bmad-bmm-dev-story ; /bmad-bmm-code-review; Commit and Push to Git; /bmad-bmm-testarch-automate ; Commit and Push to Git as neeed
At the completion of each story write a brief log entry summarizing:
- Story ID/name
- Files touched,
- Ke design decision,
- Any issues auto-resolved vs thoat that required my input.