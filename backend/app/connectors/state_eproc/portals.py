"""Registry of officially-accessible NIC state eProcurement portals.

State portals run the same NIC eProcurement (Apache Tapestry) software as the
central CPPP, so they share markup and are parsed by the CPPP mapper. Each
entry becomes its own connector (distinct source name + raw directory). Hosts
and app paths are per-portal and should be confirmed before a production run.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatePortal:
    name: str            # connector source name, e.g. "eproc_maharashtra"
    label: str
    base_url: str
    app_path: str = "/nicgep/app"


STATE_PORTALS: tuple[StatePortal, ...] = (
    StatePortal("eproc_rajasthan", "Rajasthan eProcurement", "https://eproc.rajasthan.gov.in"),
    StatePortal("eproc_maharashtra", "Maharashtra eProcurement", "https://mahatenders.gov.in"),
    StatePortal("eproc_kerala", "Kerala eProcurement", "https://etenders.kerala.gov.in"),
    StatePortal("eproc_odisha", "Odisha eProcurement", "https://tendersodisha.gov.in"),
    StatePortal("eproc_westbengal", "West Bengal eProcurement", "https://wbtenders.gov.in"),
    StatePortal("eproc_karnataka", "Karnataka eProcurement", "https://eproc.karnataka.gov.in"),
)
