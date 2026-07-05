"""OWL property/individual checks.

All OWL checks are now expressed as SHACL shapes and run via pySHACL
(``semanticlint/shacl/shapes/owl_*.ttl``, dispatched by ``semanticlint.shacl.runner``):

- OWL001 — property must declare ``rdfs:domain``   → ``owl_properties.ttl``
- OWL002 — property must declare ``rdfs:range``    → ``owl_properties.ttl``
- OWL003 — individual must have a real class type  → ``owl_individuals.ttl``

Nothing is registered here anymore; the module is kept as the documented home for
any future hand-written OWL check that SHACL cannot express.
"""

from __future__ import annotations
