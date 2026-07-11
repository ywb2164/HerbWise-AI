from __future__ import annotations
import argparse
import asyncio
from knowledge_document_tools import sync

parser = argparse.ArgumentParser(
    description="Perform one bounded knowledge document sync"
)
parser.add_argument("document_code")
args = parser.parse_args()
print(asyncio.run(sync(args.document_code)))
