---
name: github-pr-review
description: Review the PR for correctness, bugs, security issues, performance problems, and maintainability. Read-only by default; never modify files changes. Show line of code which are not following below mentioned Best practices and Bad practices and suggest the remedies.
---

## Best practices

- Follow PEP 8: Maintain consistent naming conventions, indentation, and formatting.
- Use Type Hints: Define parameter and return types for better readability and maintainability.
- Follow SOLID Principles: Design classes with single responsibilities and loose coupling.
- Write Reusable Code: Avoid code duplication (DRY – Don't Repeat Yourself).
- Handle Exceptions Properly: Use specific exceptions instead of bare except.
- Use Dependency Injection: Avoid tightly coupling classes to databases, APIs, or external services.
- Write Unit Tests: Use pytest or unittest to validate functionality and edge cases.
- Secure Sensitive Data: Never hardcode passwords, API keys, or expose personal information in logs.
- Use Context Managers: Manage files, database connections, and other resources with with statements.
- Document Your Code: Write meaningful docstrings, comments, and descriptive variable and function names.


## Bad practices
- Ignoring PEP 8: Using inconsistent naming conventions, indentation, and formatting.
- Hardcoding Credentials: Storing passwords, API keys, and secrets directly in source code.
- Using Global Variables: Sharing mutable global state across multiple functions and classes.
- Poor Exception Handling: Using bare except: and silently swallowing exceptions.
- Code Duplication: Repeating the same logic instead of creating reusable functions or methods.
- Ignoring Type Hints: Writing functions without clear parameter and return types.
- Violating SOLID Principles: Creating large classes with multiple responsibilities and tight coupling.
- Skipping Unit Tests: Not testing edge cases, failure scenarios, and business logic.
- Exposing Sensitive Data: Logging passwords, personal information, or confidential business data.
- Ignoring Resource Management: Failing to close files, database connections, and network resources properly.



- **Read-only by default.** Do not edit files, create commits, push branches, submit GitHub reviews, approve PRs, merge PRs, or change repository settings.
- Do not expose secrets. If a secret appears in a code, report its location and type without reproducing the value.


Useful read-only commands (choose only what is needed):

```bash
git status --short
git log -1 --oneline
git show --stat --oneline <commit>
git show --format=fuller --find-renames <commit>
git diff --find-renames <base>...<head>
gh pr view <PR> --json title,body,baseRefName,headRefName,files
gh pr diff <PR>
```

## Review workflow
**Establish scope.** Record the target SHA or PR number, base/head when available, and changed files.


### Security and privacy
- Authentication and authorization bypasses; missing object-level access checks.
- Injection risks (SQL, command, template, path, and deserialization).
- Unsafe handling of user input, secrets, tokens, PII, logs, and error messages.
- CORS, CSRF, cookie/session settings, cryptography, and dependency vulnerabilities where relevant.
- Excessive permissions or unsafe GitHub Actions/workflow permissions.

### Performance and reliability
- N+1 queries, unbounded loops or payloads, inefficient algorithms, and unnecessary network calls.
- Missing timeouts, unsafe retries, absent backoff, resource leaks, and blocking work in async paths.
- Cache invalidation, stale data, and consistency problems.
- Scalability and failure-mode regressions.

### Tests and maintainability
- Missing tests for changed behavior and important edge cases.
- Tests that do not assert the intended behavior or are brittle.
- Dead code, duplicated logic, confusing contracts, and unnecessary complexity.
- Configuration, migrations, dependency, and deployment compatibility.

### Stack-specific checks (when applicable)
- **Python/FastAPI:** Check for py extension files.



Use these severities:

- **P0 – Critical:** exploitable vulnerability or catastrophic data/service impact; immediate stop.
- **P1 – High:** likely serious security, data integrity, or major functional failure.
- **P2 – Medium:** a real bug or reliability/performance issue with bounded or conditional impact.
- **P3 – Low:** minor but actionable defect with limited impact.


## Output format

Start with a compact review summary:

- **Target:** commit SHA / PR number and base-to-head range if known
- **Result:** `Changes requested` or `No blocking findings`
- **Lines of code:** mention specific lines of code have any issues
- **Coverage:** files/areas inspected and checks actually run

Then list findings from highest to lowest severity. Use this format:

```text
[P1] Short, specific issue title
File: path/to/file.ext:line

What is wrong:
Explain the concrete failure scenario and why the changed code causes it.

Lines of defect:
Line1:- def get-user{}
Line2:- print(secret_key)

Suggested fix:
Give a focused remediation code fixes without applying it.
```

## Human approval boundary

Never commit, push, approve, or merge unless the user explicitly asks for that action.
