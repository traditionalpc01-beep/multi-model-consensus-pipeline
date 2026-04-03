## [ERR-20260403-001] powershell-command-separator

**Logged**: 2026-04-03T15:57:48.1717201+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
PowerShell command execution failed because `&&` is not a valid statement separator in this shell configuration.

### Error
```
所在位置 行:2 字符: 27
+ git add -- state_store.py && git commit -m "feat: add state store mod ...
+                           ~~
标记“&&”不是此版本中的有效语句分隔符。
```

### Context
- Command attempted: `git add -- state_store.py && git commit -m "feat: add state store module"`
- Environment: workspace shell is PowerShell on Windows
- The failure happened during the task-3 commit step

### Suggested Fix
Use separate shell invocations for sequential git commands in PowerShell, or use `;` when safe.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md

---
