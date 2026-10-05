import { useState, type ChangeEvent, type FormEvent } from 'react';

import { uploadWasteImage } from '../api/client';
import type { WasteDetection, WasteDetectionResult, ZoneSummary } from '../api/types';

interface WasteDetectionPanelProps {
  zones: ZoneSummary[];
  detections: WasteDetection[];
  onUploaded: () => Promise<void>;
}

function wasteLevelClass(level: string) {
  return `waste-level waste-level--${level.toLowerCase()}`;
}

function formatConfidence(confidence: number | null) {
  return confidence === null ? 'Confidence unavailable' : `${Math.round(confidence * 100)}% confidence`;
}

function DetectionResult({ result }: { result: WasteDetectionResult }) {
  return (
    <div className="waste-result" aria-live="polite">
      <div className="waste-result__heading">
        <div>
          <span className="eyebrow">Detector output</span>
          <strong>{result.detected_object_count} detected objects</strong>
        </div>
        <span className={wasteLevelClass(result.waste_level)}>{result.waste_level}</span>
      </div>

      <div className={`detector-provenance ${result.is_mock ? 'is-mock' : 'is-model'}`}>
        <span className="detector-provenance__mark" aria-hidden="true">
          {result.is_mock ? 'M' : 'CV'}
        </span>
        <span>
          <strong>{result.is_mock ? 'Mock / simulated detections' : 'Model detections'}</strong>
          <small>{result.model_name}</small>
        </span>
      </div>

      {result.detected_objects.length === 0 ? (
        <div className="waste-empty-result">No objects were returned by this detector.</div>
      ) : (
        <ul className="detected-object-list">
          {result.detected_objects.map((object, index) => (
            <li key={`${object.class_name}-${index}`}>
              <span className="object-index">{String(index + 1).padStart(2, '0')}</span>
              <strong>{object.class_name}</strong>
              <span>{formatConfidence(object.confidence)}</span>
              {object.bounding_box && (
                <small>
                  Box {Object.values(object.bounding_box).map((value) => Math.round(value)).join(', ')}
                </small>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="waste-rule-result">
        <div>
          <span>Waste classes counted</span>
          <strong>{result.waste_object_count}</strong>
        </div>
        <div>
          <span>Zone status</span>
          <strong>{result.zone_status}</strong>
        </div>
        <p>
          {result.incident_created
            ? 'A waste incident was created.'
            : result.incident_updated
              ? 'The active waste incident was updated.'
              : 'No waste incident threshold was reached.'}
        </p>
      </div>
    </div>
  );
}

export function WasteDetectionPanel({ zones, detections, onUploaded }: WasteDetectionPanelProps) {
  const [zoneId, setZoneId] = useState(zones[0]?.id ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<WasteDetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!zoneId || !file || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const detection = await uploadWasteImage(zoneId, file);
      setResult(detection);
      await onUploaded();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Image analysis failed.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="content-section waste-section" id="waste-detection">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Computer vision / Rule-based severity</p>
          <h2>Waste detection</h2>
        </div>
        <span className="section-count">Image analysis</span>
      </div>

      <div className="waste-workbench">
        <form className="waste-upload-form" onSubmit={handleSubmit}>
          <div className="waste-upload-form__intro">
            <span className="upload-symbol" aria-hidden="true">IMG</span>
            <div>
              <strong>Analyze a campus image</strong>
              <p>
                Detector labels are not campus-waste-specific. Only configured waste labels count
                toward fixed-rule severity.
              </p>
            </div>
          </div>

          <label className="form-label" htmlFor="waste-zone">Campus zone</label>
          <select
            id="waste-zone"
            value={zoneId}
            onChange={(event) => setZoneId(event.target.value)}
            disabled={isSubmitting || zones.length === 0}
          >
            {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
          </select>

          <label className="form-label" htmlFor="waste-image">Image file</label>
          <input
            id="waste-image"
            className="image-file-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            disabled={isSubmitting}
          />
          <label className="file-picker" htmlFor="waste-image">
            <span className="file-picker__icon" aria-hidden="true">+</span>
            <span>
              <strong>{file ? file.name : 'Choose an image'}</strong>
              <small>{file ? `${(file.size / 1024).toFixed(0)} KB` : 'JPEG, PNG, or WebP / 10 MB max'}</small>
            </span>
            <span className="file-picker__action">Browse</span>
          </label>

          <button
            className="button button--primary waste-submit"
            type="submit"
            disabled={!file || !zoneId || isSubmitting}
          >
            {isSubmitting ? <><span className="mini-spinner" /> Analyzing image...</> : 'Analyze image'}
          </button>

          {error && <p className="waste-error" role="alert">{error}</p>}
          <p className="waste-note">
            Local storage fallback. Mock results are simulated and are not visual analysis.
          </p>
        </form>

        <div className="waste-output">
          {result ? (
            <DetectionResult result={result} />
          ) : detections.length > 0 ? (
            <div className="waste-history">
              <div className="waste-output__heading">
                <span className="eyebrow">Recent analyses</span>
                <span>{detections.length}</span>
              </div>
              <ul>
                {detections.slice(0, 4).map((detection) => (
                  <li key={detection.id}>
                    <div>
                      <strong>{detection.zone_name}</strong>
                      <span>
                        {detection.waste_object_count} waste classes counted
                        {detection.is_mock ? ' / MOCK' : ''}
                      </span>
                    </div>
                    <span className={wasteLevelClass(detection.waste_level)}>
                      {detection.waste_level}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="waste-output-empty">
              <span className="waste-output-empty__grid" aria-hidden="true">+</span>
              <strong>Detection output appears here</strong>
              <p>Choose a zone and image to record detector output and its rule-based waste level.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}