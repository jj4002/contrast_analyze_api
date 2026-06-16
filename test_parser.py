import sys
import io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.agents.clause_parser import parse_contract
from services.document.parser import parse_document

file_path = "../Mau-hop-dong-lao-dong.docx"
text = parse_document(file_path, ".docx")

print(f"Extracted {len(text)} chars\n")

result = parse_contract(text, contract_id="test-001")

fields = [
    ("contract_type", result.contract_type),
    ("execution_date", result.execution_date),
    ("start_date", result.start_date),
    ("end_date", result.end_date),
    ("contract_value", result.contract_value),
    ("payment_method", result.payment_method),
    ("payment_terms", result.payment_terms),
    ("governing_law", result.governing_law),
    ("dispute_resolution", result.dispute_resolution),
    ("penalty_clause", result.penalty_clause),
    ("indemnity", result.indemnity),
    ("termination_clause", result.termination_clause),
    ("force_majeure", result.force_majeure),
    ("confidentiality", result.confidentiality),
    ("severability", result.severability),
    ("amendments", result.amendments),
]

for label, val in fields:
    display = val[:200] if val else "None"
    print(f"{label}: {display}")

print(f"\nPARTIES ({len(result.parties)}):")
for p in result.parties:
    for f in ['name', 'role', 'address', 'tax_id', 'representative']:
        print(f"  {f}: {getattr(p, f)}")
    print()

print(f"CLAUSES ({len(result.clauses)}):")
for c in result.clauses:
    title = c.title or '(no title)'
    summary = c.summary[:120] if c.summary else ''
    print(f"  D. {c.clause_number}: {title}")
    print(f"    {summary}...")
    print()
