---
argument-hint: --detail | --concise
---

## Git commit and push

Add all changes to git, create a commit with a descriptive message based on the work completed. Use $ARGUMENTS to control commit message detail level:

- `--detail`: Generate detailed commit message with comprehensive description of changes
- `--concise`: Generate concise commit message with brief summary only  
- No arguments: Default to concise format

**Commit Message Rules:**
- Use standard professional commit message conventions
- Do not reference AI tools, assistants, automated systems, Claude Code, or associated configuration files
- Focus on business logic, features, and application changes only
- Exclude any tooling or AI-related setup from commit descriptions
- For detailed format: Include summary, bullet points of major changes, and impact
- For concise format: Single line summary of primary change

Push to the remote repository after committing.
