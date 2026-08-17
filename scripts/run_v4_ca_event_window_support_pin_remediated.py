"""Run frozen V4 CA event-window support with the preflight SHA pin correction."""

from __future__ import annotations

from pathlib import Path

from v4_ca_input_pin_remediation import execute_remediated_script


execute_remediated_script(Path(__file__).with_name("run_v4_ca_event_window_support.py"))
