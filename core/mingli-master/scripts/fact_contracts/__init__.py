"""Provider-owned fact contracts (internal seam).

A FactContract validates one Provider's fact-layer payload and returns
structured findings. It owns the Provider's fact shape, cross-field
consistency, version/status constraints and independent oracles. It never
judges final prose, routes by keywords, selects models, gates answers after
``complete``, or performs any Gateway/LLM work.
"""

from fact_contracts.common import FactContract, finding  # noqa: F401
from fact_contracts.registry import (  # noqa: F401
    FactContractError,
    FactContractRegistry,
)
