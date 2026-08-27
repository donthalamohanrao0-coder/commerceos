# CommerceOS — RAG Security

## 1. Tenant Isolation

Every merchant has a Pinecone namespace.

Retrieval must always specify the authenticated merchant namespace.

## 2. Metadata

Store metadata such as:
- merchant_id
- document_id
- document_version
- document_type
- chunk_id

## 3. Ingestion

```text
Upload
 -> malware/file validation
 -> parse
 -> sanitize
 -> chunk
 -> embed
 -> Pinecone namespace
```

## 4. Untrusted Content

Documents are evidence, not instructions.

## 5. Retrieval

Do not retrieve across merchant namespaces.

## 6. Grounding

When appropriate, responses should cite the source document.

## 7. Versioning

Document versions should be tracked so retrieval can be audited.

## 8. Deletion

Deleting a document must remove/deactivate its associated vectors.

## 9. Poisoning

Be cautious with:
- malicious documents
- irrelevant documents
- duplicated content
- prompt injection text

## 10. Evaluation

Test retrieval for:
- relevance
- tenant isolation
- correct source
- outdated document avoidance
