"""Run graph construction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.librarian.graph_constructor import GraphConstructor
from src.librarian.graph_db import OuroborosGraphDB

db = OuroborosGraphDB()
gc = GraphConstructor(db)
stats = gc.construct_all_edges('g:/Just a Idea/tests/test_project')

print()
print('=' * 60)
print('Graph Construction Results')
print('=' * 60)
print(f'IMPORTS edges:     {stats["imports_created"]}')
print(f'INHERITS edges:    {stats["inheritance_created"]}')
print(f'CALLS edges:       {stats["calls_created"]}')
print(f'Errors:            {len(stats["errors"])}')
print('=' * 60)

db.close()
