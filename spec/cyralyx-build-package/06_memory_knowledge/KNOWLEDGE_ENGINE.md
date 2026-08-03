# Knowledge Engine

Required features:

- Markdown storage
- frontmatter
- tags
- backlinks
- outgoing links
- unresolved links
- orphan detection
- daily notes
- templates
- file history
- full-text search
- semantic search
- graph relationships
- source provenance
- project scoping

## Retrieval order

1. exact identifiers
2. project scope
3. metadata filters
4. full-text search
5. semantic search
6. graph expansion
7. recency ranking
8. reranking

Every answer using retrieved knowledge should be able to show:

- searched sources
- selected passages
- ranking reason
- timestamps
- stale-source warnings
- missing-evidence warnings
