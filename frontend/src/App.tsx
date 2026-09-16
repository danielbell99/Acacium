import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  FileText,
  Play,
  RefreshCw,
  ShieldCheck,
  Download,
  Eye,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { api, type Signal } from "./api";

function scoreClass(score: number): string {
  if (score >= 80) return "score score-high";
  if (score >= 70) return "score score-medium";
  return "score score-low";
}

function formatTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function EvidencePanel({
  signal,
  onReview,
  reviewReason,
  onReviewReasonChange,
  reviewing,
  readOnly,
}: {
  signal: Signal | undefined;
  onReview: (decision: "approved" | "rejected", reason: string) => void;
  reviewReason: string;
  onReviewReasonChange: (reason: string) => void;
  reviewing: boolean;
  readOnly: boolean;
}) {
  if (!signal) {
    return (
      <aside className="detail-empty">
        Select a ranked signal to inspect its source evidence.
      </aside>
    );
  }

  return (
    <aside className="detail-panel" aria-label="Signal evidence">
      <div className="detail-heading">
        <span className={scoreClass(signal.score)}>
          {signal.score.toFixed(1)}
        </span>
        <div>
          <p className="eyebrow">{signal.category}</p>
          <h2>{signal.organisation}</h2>
        </div>
      </div>
      <section>
        <h3>Source fact</h3>
        <blockquote>{signal.source_fact}</blockquote>
        <p className="citation">
          <FileText size={15} aria-hidden="true" /> {signal.evidence.filename},
          physical page {signal.evidence.physical_page}
        </p>
        <a
          className="evidence-link"
          href={`/api/documents/${signal.evidence.document_id}/content#page=${signal.evidence.physical_page}`}
          target="_blank"
          rel="noreferrer"
        >
          Open original PDF
        </a>
      </section>
      <section>
        <h3>Interpretation</h3>
        <p>{signal.interpretation}</p>
      </section>
      <section>
        <h3>Score rationale</h3>
        <ul>
          {signal.score_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>
      <section>
        <h3>Suggested next action</h3>
        <p>{signal.proposed_next_action}</p>
      </section>
      <section>
        <h3>Review decision</h3>
        <p className={`review-status status-${signal.review_status}`}>
          {signal.review_status}
        </p>
        {signal.review_reason ? (
          <p className="saved-review-reason">{signal.review_reason}</p>
        ) : null}
        {readOnly ? (
          <p className="historical-note">Retained historical snapshot.</p>
        ) : (
          <>
            <label className="review-reason" htmlFor="review-reason">
              Reviewer rationale
              <textarea
                id="review-reason"
                value={reviewReason}
                onChange={(event) => onReviewReasonChange(event.target.value)}
                maxLength={500}
                placeholder="State why the evidence should be approved or rejected."
              />
            </label>
            <div className="review-actions">
              <button
                className="approve"
                disabled={reviewing || reviewReason.trim().length < 3}
                onClick={() => onReview("approved", reviewReason.trim())}
              >
                <ThumbsUp size={15} aria-hidden="true" /> Approve
              </button>
              <a className="export-button" href="/api/shortlist/export" download>
                <Download size={17} aria-hidden="true" /> Export approved
              </a>
              <button
                className="reject"
                disabled={reviewing || reviewReason.trim().length < 3}
                onClick={() => onReview("rejected", reviewReason.trim())}
              >
                <ThumbsDown size={15} aria-hidden="true" /> Reject
              </button>
            </div>
          </>
        )}
      </section>
      <p className="caveat">
        <AlertCircle size={15} aria-hidden="true" /> {signal.caveats[0]}
      </p>
    </aside>
  );
}

export default function App() {
  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>();
  const [historicalRunId, setHistoricalRunId] = useState<string>();
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>();
  const [reviewReason, setReviewReason] = useState("");
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: api.documents,
  });
  const signals = useQuery({
    queryKey: ["signals"],
    queryFn: api.signals,
    refetchInterval: 2500,
  });
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: api.jobs,
    refetchInterval: 2500,
  });
  const historicalSignals = useQuery({
    queryKey: ["run-signals", historicalRunId],
    queryFn: () => api.runSignals(historicalRunId as string),
    enabled: Boolean(historicalRunId),
  });
  const run = useMutation({
    mutationFn: api.startRun,
    onSuccess: () => void client.invalidateQueries({ queryKey: ["jobs"] }),
  });
  const review = useMutation({
    mutationFn: ({
      signalId,
      decision,
      reason,
    }: {
      signalId: string;
      decision: "approved" | "rejected";
      reason: string;
    }) => api.reviewSignal(signalId, decision, reason),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["signals"] }),
  });

  const displayedSignals = useMemo(
    () => historicalSignals.data ?? signals.data ?? [],
    [historicalSignals.data, signals.data],
  );
  const shortlist = useMemo(
    () => displayedSignals.filter((signal) => signal.score >= 70),
    [displayedSignals],
  );
  const selected =
    shortlist.find((signal) => signal.id === selectedId) ?? shortlist[0];

  const activeRun = jobs.data?.find(
    (job) => job.status === "queued" || job.status === "running",
  );
  const latestCompletedRun = jobs.data?.find((job) => job.status === "completed");
  const historicalRun = jobs.data?.find((job) => job.id === historicalRunId);
  const recentRuns = useMemo(() => (jobs.data ?? []).slice(0, 3), [jobs.data]);
  const selectedDocuments = useMemo(() => {
    const available = documents.data?.documents ?? [];
    if (selectedDocumentIds === undefined) {
      return available;
    }
    return available.filter((document) =>
      selectedDocumentIds.includes(document.id),
    );
  }, [documents.data?.documents, selectedDocumentIds]);
  const selectedPageCount = selectedDocuments.reduce(
    (count, document) => count + document.scope.page_count,
    0,
  );

  function toggleDocument(documentId: string): void {
    const defaultIds =
      documents.data?.documents.map((document) => document.id) ?? [];
    setSelectedDocumentIds((current) => {
      const selected = current ?? defaultIds;
      return selected.includes(documentId)
        ? selected.filter((id) => id !== documentId)
        : [...selected, documentId];
    });
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span>Acacium</span>
          <strong>Board Paper Intelligence</strong>
        </div>
        <div className="mode">
          <ShieldCheck size={16} aria-hidden="true" /> Local evidence-first
          prototype
        </div>
      </header>
      <section className="workspace">
        <div className="workspace-header">
          <div>
            <p className="eyebrow">Ranked shortlist</p>
            <h1>Workforce signals with their evidence intact.</h1>
          </div>
          <button
            className="run-button"
            onClick={() =>
              run.mutate(selectedDocuments.map((document) => document.id))
            }
            disabled={
              !documents.data ||
              selectedDocuments.length === 0 ||
              Boolean(activeRun) ||
              run.isPending
            }
          >
            {activeRun || run.isPending ? (
              <RefreshCw size={17} className="spin" aria-hidden="true" />
            ) : (
              <Play size={17} aria-hidden="true" />
            )}
            {activeRun ? "Extraction running" : "Run selected corpus"}
          </button>
        </div>
        <div className="coverage-strip">
          <span>{selectedDocuments.length} source packs selected</span>
          <span>{selectedPageCount} declared pages in scope</span>
          <span>
            {activeRun
              ? `${activeRun.progress.processed_pages}/${activeRun.progress.selected_pages} pages processed`
              : "No active run"}
          </span>
        </div>
        {documents.data ? (
          <fieldset className="source-selector">
            <legend>Source packs</legend>
            <div className="source-options">
              {documents.data.documents.map((document) => (
                <label key={document.id} className="source-option">
                  <input
                    type="checkbox"
                    checked={selectedDocuments.some(
                      (selected) => selected.id === document.id,
                    )}
                    onChange={() => toggleDocument(document.id)}
                  />
                  <span>
                    <strong>{document.organisation}</strong>
                    <small>
                      {document.scope.page_count} pages ·{" "}
                      {document.scope.layout}
                    </small>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}
        {recentRuns.length > 0 ? (
          <section
            className="run-history"
            aria-label="Recent extraction history"
          >
            <div className="run-history-heading">
              <p className="eyebrow">Recent extractions</p>
              <span>{recentRuns.length} retained locally</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Corpus</th>
                  <th>Provenance</th>
                  <th>Status</th>
                  <th>Signals found</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((job) => (
                  <tr key={job.id}>
                    <td>{formatTimestamp(job.created_at)}</td>
                    <td>{job.document_ids.length} source packs</td>
                    <td>
                      <span
                        title={`As of ${job.as_of_date}; rubric ${job.rubric_version}; service catalogue ${job.service_catalogue_version}`}
                      >
                        manifest {job.source_manifest_version}
                      </span>
                    </td>
                    <td>
                      <span className={`run-status run-${job.status}`}>
                        {job.status.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td>{job.progress.candidates_found}</td>
                    <td>
                      {job.id === latestCompletedRun?.id ? (
                        <span className="current-run">Current</span>
                      ) : (
                        <button
                          className="history-button"
                          type="button"
                          onClick={() => {
                            setHistoricalRunId(
                              historicalRunId === job.id ? undefined : job.id,
                            );
                            setSelectedId(undefined);
                            setReviewReason("");
                          }}
                        >
                          <Eye size={15} aria-hidden="true" />
                          {historicalRunId === job.id ? "Current" : "View"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}
        {signals.isError || historicalSignals.isError ? (
            <p className="error">
            The API is not available yet. Start the local services and refresh
            this page.
          </p>
        ) : null}
        <div className="content-grid">
          <section className="shortlist" aria-label="Ranked shortlist">
            {historicalRun ? (
              <p className="historical-banner">
                Viewing retained evidence from {formatTimestamp(historicalRun.created_at)}
              </p>
            ) : null}
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Organisation</th>
                  <th>Signal</th>
                  <th>Period</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {shortlist.map((signal, index) => (
                  <tr
                    key={signal.id}
                    className={selected?.id === signal.id ? "selected" : ""}
                    onClick={() => {
                      setSelectedId(signal.id);
                      setReviewReason("");
                    }}
                  >
                    <td>{index + 1}</td>
                    <td>{signal.organisation}</td>
                    <td>{signal.category}</td>
                    <td>{signal.reporting_period ?? "Unknown"}</td>
                    <td>
                      <span className={scoreClass(signal.score)}>
                        {signal.score.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
                {!signals.isLoading && !historicalSignals.isLoading && shortlist.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty">
                      Run the selected corpus to generate reviewable candidates.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </section>
          <EvidencePanel
            signal={selected}
            reviewing={review.isPending}
            readOnly={Boolean(historicalRun)}
            reviewReason={reviewReason}
            onReviewReasonChange={setReviewReason}
            onReview={(decision, reason) =>
              selected &&
              review.mutate({ signalId: selected.id, decision, reason })
            }
          />
        </div>
      </section>
    </main>
  );
}
