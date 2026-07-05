"""RDFS/OWL class checks.

All RDFS class checks are now expressed as SHACL shapes and run via pySHACL
(``semanticlint/shacl/shapes/rdfs_*.ttl``, dispatched by ``semanticlint.shacl.runner``):

- RDS001 — class must have an ``rdfs:label``                     → ``rdfs_classes.ttl``
- RDS002 — ``rdfs:subClassOf`` must reference a declared class   → ``rdfs_subclass.ttl``

Nothing is registered here anymore; the module is kept as the documented home for
any future hand-written RDFS check that SHACL cannot express.
"""

from __future__ import annotations
