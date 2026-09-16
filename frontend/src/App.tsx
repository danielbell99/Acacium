import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  FileText,
  Play,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { api, type Signal } from "./api";

function scoreClass(score: number): string {
  if (score >= 80) return "score score-high";
  if (score >= 70) return "score score-medium";
  return "score score-low";
}

function EvidencePanel({ signal }: { signal: Signal | undefined }) {
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
      <p className="caveat">
        <AlertCircle size={15} aria-hidden="true" /> {signal.caveats[0]}
      </p>
    </aside>
  );
}

export default function App() {
  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>();
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
  const run = useMutation({
    mutationFn: api.startRun,
    onSuccess: () => void client.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const shortlist = useMemo(
    () => (signals.data ?? []).filter((signal) => signal.score >= 70),
    [signals.data],
  );
  const selected =
    shortlist.find((signal) => signal.id === selectedId) ?? shortlist[0];

  const activeRun = jobs.data?.find(
    (job) => job.status === "queued" || job.status === "running",
  );

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
              run.mutate(
                documents.data?.documents.map((document) => document.id) ?? [],
              )
            }
            disabled={!documents.data || Boolean(activeRun) || run.isPending}
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
          <span>{documents.data?.documents.length ?? 0} source packs</span>
          <span>
            {documents.data?.selected_report_page_count ?? 0} declared pages in
            scope
          </span>
          <span>
            {activeRun
              ? `${activeRun.progress.processed_pages}/${activeRun.progress.selected_pages} pages processed`
              : "No active run"}
          </span>
        </div>
        {signals.isError ? (
          <p className="error">
            The API is not available yet. Start the local services and refresh
            this page.
          </p>
        ) : null}
        <div className="content-grid">
          <section className="shortlist" aria-label="Ranked shortlist">
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
                    onClick={() => setSelectedId(signal.id)}
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
                {!signals.isLoading && shortlist.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty">
                      Run the selected corpus to generate reviewable candidates.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </section>
          <EvidencePanel signal={selected} />
        </div>
      </section>
    </main>
  );
}
