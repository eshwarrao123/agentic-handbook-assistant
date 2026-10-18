/**
 * CitationCard — renders a single RAG citation from the API response.
 * Structured data from reply.citations[]; never invents source names or pages.
 */

import type { Citation } from '../api/types';
import './CitationCard.css';

interface Props {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: Props) {
  return (
    <div className="citation-card" role="listitem">
      <div className="citation-header">
        <span className="citation-index" aria-label={`Citation ${index + 1}`}>
          [{index + 1}]
        </span>
        <span className="citation-document">{citation.title || citation.document}</span>
        <span className="citation-page">p.&nbsp;{citation.page}</span>
      </div>
      {citation.snippet && (
        <blockquote className="citation-snippet">{citation.snippet}</blockquote>
      )}
      <div className="citation-meta">
        <span className="citation-chunk-id" title={`Chunk: ${citation.chunk_id}`}>
          {citation.document}
        </span>
      </div>
    </div>
  );
}

interface CitationsProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationsProps) {
  if (citations.length === 0) return null;

  return (
    <details className="citations-disclosure">
      <summary className="citations-summary">
        <span className="citations-icon" aria-hidden="true">📄</span>
        {citations.length === 1 ? '1 source' : `${citations.length} sources`}
      </summary>
      <div className="citations-list" role="list" aria-label="Sources">
        {citations.map((c, i) => (
          <CitationCard key={c.chunk_id} citation={c} index={i} />
        ))}
      </div>
    </details>
  );
}
