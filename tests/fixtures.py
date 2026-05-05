from __future__ import annotations

VALID_SKOS_TURTLE = """\
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <http://example.org/> .

ex:Scheme a skos:ConceptScheme .
ex:Concept1 a skos:Concept ;
    skos:inScheme ex:Scheme ;
    skos:prefLabel "Concept 1"@en .
"""

INVALID_TURTLE = """\
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <http://example.org/> .
ex:Concept1 a skos:Concept
"""

VALID_OWL_TURTLE = """\
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:MyOntology a owl:Ontology .
ex:MyClass a owl:Class .
"""

VALID_RDFS_TURTLE = """\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:MyClass a rdfs:Class .
"""

VALID_PLAIN_RDF_TURTLE = """\
@prefix ex: <http://example.org/> .

ex:subject ex:predicate ex:object .
"""

VALID_RDFXML = """\
<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">
  <rdf:Description rdf:about="http://example.org/subject">
    <ex:predicate rdf:resource="http://example.org/object"/>
  </rdf:Description>
</rdf:RDF>
"""

VALID_JSONLD = """\
{
  "@context": {"ex": "http://example.org/"},
  "@id": "http://example.org/subject",
  "http://example.org/predicate": [{"@id": "http://example.org/object"}]
}
"""

VALID_NTRIPLES = (
    "<http://example.org/subject> <http://example.org/predicate> <http://example.org/object> .\n"
)
