import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enterprise_rag.auth import seed_reference_users
from enterprise_rag.config import get_settings
from enterprise_rag.database import connect, init_db
from enterprise_rag.ingestion import ingest_documents


def main() -> None:
    settings = get_settings()
    with connect(settings.database_path) as conn:
        init_db(conn)
        seed_reference_users(conn)
        result = ingest_documents(conn, settings.document_path)
    print(f"Ingested {result['documents']} documents and {result['chunks']} chunks.")
    print("Seeded reference users: emma.employee, eric.engineer, fatima.finance, ava.admin.")


if __name__ == "__main__":
    main()
