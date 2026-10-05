import { useEffect, useState } from 'react';

import {
  generateIncidentRecommendation,
  getIncidentRecommendation,
} from '../api/client';
import type { IncidentRecommendation } from '../api/types';

function formatTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function RecommendationPanel({ incidentId }: { incidentId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [recommendation, setRecommendation] = useState<IncidentRecommendation | null>(null);
  const [isLoadingSaved, setIsLoadingSaved] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadLatest() {
    setIsLoadingSaved(true);
    setError(null);
    try {
      setRecommendation(await getIncidentRecommendation(incidentId));
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Saved recommendation could not be loaded.',
      );
    } finally {
      setIsLoadingSaved(false);
    }
  }

  useEffect(() => {
    void loadLatest();
  }, [incidentId]);

  async function generate() {
    setIsGenerating(true);
    setError(null);
    try {
      setRecommendation(await generateIncidentRecommendation(incidentId));
      setIsOpen(true);
    } catch (generationError) {
      setError(
        generationError instanceof Error
          ? generationError.message
          : 'Recommendation could not be generated.',
      );
    } finally {
      setIsGenerating(false);
    }
  }

  const factsById = new Map(recommendation?.facts.map((fact) => [fact.id, fact]) ?? []);

  return (
    <div className="recommendation-control">
      <div className="recommendation-control__buttons">
        <button
          className="recommendation-trigger"
          type="button"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((open) => !open)}
        >
          <span className="recommendation-trigger__mark" aria-hidden="true">AI</span>
          {recommendation ? 'View recommendation' : 'Generate explanation'}
        </button>
        {recommendation && isOpen && (
          <button
            className="recommendation-retry"
            type="button"
            disabled={isGenerating}
            onClick={() => void generate()}
          >
            {isGenerating ? 'Generating...' : 'Generate again'}
          </button>
        )}
      </div>

      {isOpen && (
        <div className="recommendation-detail">
          {isLoadingSaved ? (
            <p className="recommendation-status" role="status">Checking saved recommendations...</p>
          ) : error ? (
            <div className="recommendation-error" role="alert">
              <span>{error}</span>
              <button type="button" onClick={() => void loadLatest()}>Retry</button>
              <button type="button" onClick={() => void generate()}>Generate</button>
            </div>
          ) : isGenerating ? (
            <p className="recommendation-status" role="status">Preparing incident-grounded guidance...</p>
          ) : recommendation ? (
            <>
              <div className="recommendation-provenance">
                <span
                  className={`recommendation-mode recommendation-mode--${recommendation.mode}`}
                >
                  {recommendation.mode === 'ai' ? 'AI advisory' : 'Rule-based fallback'}
                </span>
                <span>{recommendation.provider} / {recommendation.model}</span>
                <time>{formatTime(recommendation.generated_at)}</time>
              </div>

              {recommendation.mode === 'fallback' && recommendation.fallback_reason && (
                <p className="recommendation-fallback-note">{recommendation.fallback_reason}</p>
              )}

              <section className="recommendation-facts" aria-label="Measured and rule-based incident facts">
                <h4>Measured / rule-based facts</h4>
                <dl>
                  {recommendation.facts.map((fact) => (
                    <div key={fact.id}>
                      <dt>{fact.label}</dt>
                      <dd>{fact.value}</dd>
                    </div>
                  ))}
                </dl>
                <small>Values above are from stored incident and zone records.</small>
              </section>

              <section className="recommendation-advisory" aria-label="Generated advisory">
                <h4>{recommendation.mode === 'ai' ? 'AI-generated explanation' : 'Fallback explanation'}</h4>
                <p>{recommendation.explanation}</p>
                <h4>Suggested actions</h4>
                <ol>
                  {recommendation.recommendations.map((item, index) => (
                    <li key={`${item.title}-${index}`}>
                      <strong>{item.title}</strong>
                      <p>{item.action}</p>
                      <small>{item.rationale}</small>
                      <span className="recommendation-evidence">
                        Evidence: {item.supporting_fact_ids
                          .map((factId) => factsById.get(factId)?.label ?? factId)
                          .join(', ')}
                      </span>
                    </li>
                  ))}
                </ol>
                <p className="recommendation-disclaimer">
                  Advisory only. Existing rule-based incident detection remains authoritative.
                </p>
              </section>
            </>
          ) : (
            <div className="recommendation-empty">
              <p>No saved recommendation yet. Generate one from the incident facts.</p>
              <button
                className="button button--primary"
                type="button"
                disabled={isGenerating}
                onClick={() => void generate()}
              >
                {isGenerating ? 'Generating...' : 'Generate explanation'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}