# Document Query Store Insights

## Vector Store Pitfalls

1. **FAISS Vector Search Limitations**
   - Vector search methods often have internal limits regardless of the `limit` parameter
   - Empty queries with URI filters don't work reliably through vector search
   - Direct docstore access is more reliable for document retrieval by URI

2. **URI Normalization Inconsistencies**
   - Different URI normalization between storing vs retrieving causes "document not found" errors
   - Web URIs need consistent http/https normalization
   - File paths need consistent file:// vs file: handling
   - Centralized normalization is essential for reliable document operations

3. **Chunking Considerations**
   - Long documents (particularly HTML) may have search terms split across chunk boundaries
   - Embeddings don't perform well for exact text matching, only semantic similarity
   - Default thresholds (0.5-0.7) are often too high for practical document search
   - Fallback to lower thresholds (0.3) can improve results significantly

4. **Database Access Patterns**
   - Direct docstore access (`vectorstore.docstore._dict`) is more reliable than vector search APIs
   - Combined documents should preserve metadata except for chunk-specific fields
   - When chunks span different parts of a document, sorting by chunk_index is critical

## Implementation Techniques

1. **Simplified Architecture**
   - Creating database directly where it needs to be, not in temp dirs
   - Avoiding unnecessary complexity with file operations and copies
   - URI-based API rather than working with internal IDs

2. **Reliability Strategies**
   - Always normalize URIs the same way throughout the codebase
   - Implement fallback mechanisms (like lower thresholds) when initial searches fail
   - Explicitly add error messages to identify specific failure points
   - Use consistent access patterns for retrieval

3. **Performance Insights**
   - Embedding and storing large documents is expensive - centralize chunking
   - Threshold tuning is essential: too high misses relevant content, too low includes noise
   - Expire mechanism should check only first chunks to avoid redundant timestamp checks
