# Contributing

Thanks for your interest in improving this project.

## Quick Setup

1. Fork the repository.
2. Clone your fork.
3. Run:

```bash
setup_entorno.bat
```

4. Start the app:

```bash
iniciar_monitor_github.bat
```

## Development Workflow

1. Create a branch from `multilenguaje` (or the active default branch).
2. Make focused changes.
3. Validate before opening a PR:

```bash
python -m py_compile copilot_usage_monitor.py
```

4. Update docs if behavior or UX changed.
5. Open a Pull Request with context, screenshots, and testing notes.

## What We Welcome

- Bug fixes and stability improvements.
- UX improvements (especially taskbar mode).
- Better docs and onboarding.
- Platform support improvements (Windows/Linux).

## Pull Request Checklist

- [ ] Change is scoped and understandable.
- [ ] Code compiles locally.
- [ ] README/docs updated if needed.
- [ ] No sensitive/local files included.
- [ ] Steps to reproduce/verify are included.

## Reporting Issues

Please include:

- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (`monitor_runtime.log`, `monitor_crash.log`)
- Screenshot/GIF if UI-related
