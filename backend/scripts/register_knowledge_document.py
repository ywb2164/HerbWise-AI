from __future__ import annotations
import argparse
import asyncio
from knowledge_document_tools import register

parser = argparse.ArgumentParser(
    description="Register an uploaded, authorised document without syncing it"
)
parser.add_argument("uploaded_file_id")
parser.add_argument("dataset_code")
args = parser.parse_args()
print(asyncio.run(register(args.uploaded_file_id, args.dataset_code)))
