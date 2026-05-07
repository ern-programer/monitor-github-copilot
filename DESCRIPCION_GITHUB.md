# GitHub Copilot Monitor

Visual monthly usage monitor for GitHub Copilot Premium requests, designed to keep one or multiple accounts always visible.

## What this project is

This Python app reads the authenticated GitHub Copilot Features page and displays a floating bar with:

- current usage percentage
- visual progress bar
- usage pace and monthly projection
- plan status and reset note (when provided by GitHub)

## What it is useful for

- avoiding end-of-month usage surprises
- monitoring multiple accounts in one window
- keeping a lightweight taskbar-style indicator without opening the browser

## Main features

- movable floating UI, configurable opacity, always-on-top
- compact taskbar mode (70, 100, and 150 px)
- system tray support (restore, refresh, exit)
- multi-account support
- guided login with persistent session
- single-instance behavior with bring-to-front
- persistent INI configuration and in-app settings menu
- hot-switch language (English/Spanish) and theme (dark/light)

## Platforms

- Windows: full support
- Linux: separate version in monitor_github_linux

## Privacy and scope

The project does not use an official public API endpoint for this value. It reads data from the user's authenticated GitHub settings page. Session state is stored locally to avoid frequent re-login.

## Quick start

1. Run setup_entorno.bat
2. Run iniciar_monitor_github.bat
3. On first run, complete login when prompted

## Current visual version

Current visual version: v1.3.1
