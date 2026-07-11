"""Facade: deterministic procurement taxonomy classifiers."""
from app.services.procurement_taxonomy import (  # noqa: F401
    authority_of, category_of, department_of, ministry_of,
    procurement_method_of, state_of, year_of,
    INDIAN_STATES, OTHER, UNATTRIBUTED, UNSPECIFIED,
)
