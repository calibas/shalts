# Git Workflow Guidelines

## CRITICAL: Branch Strategy
- Always create feature branches from `main`
- Never commit directly to `main` or `develop`
- Branch naming: `feature/description`, `fix/description`, `docs/description`

## Commit Messages
- Use conventional commits: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep the first line under 50 characters
- Add detailed description after blank line if needed

## Before Pushing
1. Run all tests: `npm test` or `pytest`
2. Check linting: `npm run lint` or `flake8`
3. Update documentation if API changed
4. Squash WIP commits if needed

## Code Review Process
- All code must be reviewed before merging
- Respond to feedback within 24 hours
- Use "Resolve conversation" when addressed
- Request re-review after making changes