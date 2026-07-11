from __future__ import annotations
import argparse
import asyncio
from knowledge_document_tools import check

parser = argparse.ArgumentParser(
    description="Read one registered knowledge document state"
)
parser.add_argument("document_code")
args = parser.parse_args()
print(asyncio.run(check(args.document_code)))
