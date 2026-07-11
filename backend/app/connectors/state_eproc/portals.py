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
    parser: str = "nic"
    notes: str = "NIC eProcurement public tender-list portal"


STATE_PORTALS: tuple[StatePortal, ...] = (
    StatePortal("eproc_rajasthan", "Rajasthan eProcurement", "https://eproc.rajasthan.gov.in"),
    StatePortal("eproc_maharashtra", "Maharashtra eProcurement", "https://mahatenders.gov.in"),
    StatePortal("eproc_karnataka", "Karnataka Public Procurement", "https://kppp.karnataka.gov.in", parser="generic"),
    StatePortal("eproc_kerala", "Kerala eProcurement", "https://etenders.kerala.gov.in"),
    StatePortal("eproc_tamilnadu", "Tamil Nadu eProcurement", "https://tntenders.gov.in"),
    StatePortal("eproc_odisha", "Odisha eProcurement", "https://tendersodisha.gov.in"),
    StatePortal("eproc_gujarat", "Gujarat eProcurement", "https://tender.nprocure.com", parser="generic"),
    StatePortal("eproc_delhi", "Delhi eProcurement", "https://govtprocurement.delhi.gov.in"),
    StatePortal("eproc_westbengal", "West Bengal eProcurement", "https://wbtenders.gov.in"),
    StatePortal("eproc_andhrapradesh", "Andhra Pradesh eProcurement", "https://tender.apeprocurement.gov.in", parser="generic"),
    StatePortal("eproc_telangana", "Telangana eProcurement", "https://tender.telangana.gov.in", parser="generic"),
    StatePortal("eproc_punjab", "Punjab eProcurement", "https://eproc.punjab.gov.in"),
    StatePortal("eproc_haryana", "Haryana eProcurement", "https://etenders.hry.nic.in"),
    StatePortal("eproc_uttarpradesh", "Uttar Pradesh eProcurement", "https://etender.up.nic.in"),
)
