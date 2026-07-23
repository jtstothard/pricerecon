## Summary
Brief description of what this PR changes and why.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring / code quality improvement
- [ ] CI/CD or infrastructure change

## Related Issues
Fixes # (issue number)
Closes # (issue number)
Related to # (issue number)

## Changes Made
List the main changes:
- Changed X to do Y
- Added feature Z
- Fixed bug in component A
- Updated documentation B

## Testing
Describe how you tested this change:
- [ ] Unit tests pass locally
- [ ] Integration tests pass locally
- [ ] Added new tests for the change
- [ ] Manual testing performed
- [ ] Tested with connector(s): (list)

### Test Commands Run
```bash
# Include commands you ran to verify
python -m pytest
python -m ruff check .
python -m mypy src/pricerecon
python -m pricerecon.quality_gate
```

## Screenshots (if applicable)
If this change affects the UI, include before/after screenshots.

## Breaking Changes
If this is a breaking change, describe:
- What breaks
- How users should migrate
- Why this break is necessary

## Checklist
- [ ] My code follows the [engineering standard](docs/engineering-standard.md)
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation (README, CONTRIBUTING, or docs/)
- [ ] My changes generate no new warnings or errors in the quality gate
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with `python -m pytest`
- [ ] I have run `python -m pricerecon.quality_gate` and it passes
- [ ] Any dependent changes have been merged and published

## Additional Notes
Any additional context, questions, or concerns.