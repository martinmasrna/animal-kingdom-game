"""Headless rules engine. Standard library only - no third-party dependencies.

Keep this package pure and transport-agnostic (see docs/engine/handoff-engine.md §4):
no I/O, no global RNG/clock, all randomness injected, all output via return values.
"""
