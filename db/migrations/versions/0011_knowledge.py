"""knowledge: documents, document_versions (circular FK resolved via ALTER TABLE)

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-25
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE documents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            title text NOT NULL,
            document_type text NOT NULL,
            storage_path text NOT NULL,
            status text NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','processing','indexed','failed','deleted')),
            current_version_id uuid,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE document_versions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            version_number int NOT NULL,
            chunk_count int,
            pinecone_namespace text NOT NULL,
            indexed_at timestamptz,
            is_active boolean NOT NULL DEFAULT true,
            UNIQUE (document_id, version_number)
        );
    """)

    op.execute("""
        ALTER TABLE documents ADD CONSTRAINT fk_documents_current_version
        FOREIGN KEY (current_version_id) REFERENCES document_versions(id);
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS fk_documents_current_version;")
    op.execute("DROP TABLE IF EXISTS document_versions;")
    op.execute("DROP TABLE IF EXISTS documents;")
