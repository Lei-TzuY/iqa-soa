"""IQA-SOA FSE experimental prototype.

QA-XML specifies executable constraints, IQA-SOA enforces them at runtime,
and QA-IUM-compatible evidence fragments preserve what happened and why.
"""

from iqa_soa.types import Action, Decision, QAMode

__all__ = ["Action", "Decision", "QAMode"]
__version__ = "0.2.0"
