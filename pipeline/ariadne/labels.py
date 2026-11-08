# Written with AI assistance (Claude Code). See AI_USE.md.
"""The four labels every number carries (CLAUDE.md rule 2)."""

from enum import StrEnum


class Label(StrEnum):
    MEASURED = "MEASURED"  # read directly from an instrument or a published measurement
    DERIVED = "DERIVED"  # computed from measured data by a documented method
    MODELED = "MODELED"  # output of a documented model
    PLACEHOLDER = "PLACEHOLDER"  # a stand-in value chosen by the team, shown as such
