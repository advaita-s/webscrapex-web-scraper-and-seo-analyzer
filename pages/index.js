// frontend/pages/index.js
import NavBar from "../components/NavBar";
import SearchForm from "../components/SearchForm";
import axios from "axios";
import { useEffect, useState } from "react";

export default function Home() {
  const [jobs, setJobs] = useState([]);
  const [lastCreated, setLastCreated] = useState(null);

  const fetchJobs = async () => {
    try {
      const resp = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE}/api/jobs`);
      setJobs(resp.data || []);
    } catch (err) {
      console.error("fetchJobs:", err);
    }
  };

  useEffect(() => {
    fetchJobs();
    const t = setInterval(fetchJobs, 25000);
    return () => clearInterval(t);
  }, []);

  const onJobCreated = (id) => {
    setLastCreated(id);
    fetchJobs();
  };

  const refreshJob = async (id) => {
    try {
      const resp = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE}/api/results/${id}`);
      setJobs((prev) =>
        prev.map((j) =>
          j.id === id
            ? {
                ...j,
                status: resp.data.status,
                result: resp.data.result,
                error: resp.data.error,
              }
            : j
        )
      );
    } catch (err) {
      console.error("refreshJob:", err);
      alert("Unable to refresh job. See console for details.");
    }
  };

  const downloadCSV = (job) => {
    if (!job.result || !job.result.data) {
      alert("No data available for this job.");
      return;
    }
    const data = job.result.data;

    const cols = Object.keys(data);
    const maxRows = Math.max(...cols.map((c) => (Array.isArray(data[c]) ? data[c].length : 1)));

    const rows = [];
    for (let r = 0; r < maxRows; r++) {
      const row = cols.map((c) => {
        const v = data[c];
        if (Array.isArray(v)) {
          return v[r] !== undefined ? String(v[r]).replace(/\n/g, " ") : "";
        } else if (v && typeof v === "object") {
          return JSON.stringify(v).replace(/\n/g, " ");
        } else {
          return r === 0 ? (v !== undefined ? String(v).replace(/\n/g, " ") : "") : "";
        }
      });
      rows.push(row);
    }

    const csv =
      [cols.join(",")].concat(
        rows.map((r) =>
          r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
        )
      ).join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scrape_${job.id}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  /* DELETE JOB */
  const deleteJob = async (id) => {
    if (!confirm("Delete this job?")) return;
    try {
      await axios.delete(`${process.env.NEXT_PUBLIC_API_BASE}/api/jobs/${id}`);
      setJobs((prev) => prev.filter((job) => job.id !== id));
    } catch (err) {
      console.error("deleteJob:", err);
      alert("Unable to delete job.");
    }
  };

  return (
    <div className="min-h-screen page-wrapper">
      <NavBar />

      <main className="max-w-5xl mx-auto py-8 px-4 space-y-8">
        <SearchForm onJobCreated={onJobCreated} />

        {/* RECENT JOBS */}
        <section className="space-y-4">
          <div className="max-w-5xl w-full mx-auto">
            <div className="card p-6 space-y-4">

              <div className="text-xl font-bold">Recent Jobs</div>

              <div className="jobs-list space-y-4">
                {jobs.length === 0 && (
                  <div className="text-sm opacity-70">No jobs yet — create one above.</div>
                )}

                {jobs.map((j) => (
                  <div key={j.id} className="card job p-4">

                    {/* =======================================================
                        FIXED LAYOUT — URL wraps but buttons stay aligned right
                       ======================================================= */}
                    <div className="flex w-full items-start">
                      
                      {/* LEFT: URL + STATUS (WRAPS) */}
                      <div className="flex-1 min-w-0 pr-4">
                        <div className="font-semibold break-words whitespace-normal">
                          {j.url}
                        </div>
                        <div className="text-sm opacity-80 mt-1">Status: {j.status}</div>
                      </div>

                      {/* RIGHT: BUTTONS STAY SIDE BY SIDE ON RIGHT */}
                      <div className="flex items-center gap-3 shrink-0">

                        <button
                          className="btn-secondary tooltip px-3 py-2"
                          data-tooltip="Refresh job"
                          onClick={() => refreshJob(j.id)}
                        >
                          Refresh
                        </button>

                        <button
                          className="btn-primary tooltip px-3 py-2"
                          data-tooltip="Download CSV"
                          onClick={() => downloadCSV(j)}
                        >
                          Download CSV
                        </button>

                        {/* Delete icon */}
                        <button
                          onClick={() => deleteJob(j.id)}
                          className="p-2 rounded"
                          title="Delete job"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#ff4444"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
                            <path d="M10 11v6"></path>
                            <path d="M14 11v6"></path>
                            <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"></path>
                          </svg>
                        </button>

                      </div>
                    </div>
                    {/* ======================================================= */}


                    {/* RESULT */}
                    {j.result && j.result.data && (
                      <div className="mt-3">
                        {j.result.data.title && (
                          <div className="font-bold">{j.result.data.title}</div>
                        )}

                        {j.result.data.paragraphs &&
                          j.result.data.paragraphs.length > 0 && (
                            <div className="text-sm opacity-80 max-h-40 overflow-auto p-2 bg-white/5 rounded mt-2">
                              {j.result.data.paragraphs.slice(0, 10).map((p, idx) => (
                                <p key={idx} className="mb-2">{p}</p>
                              ))}
                            </div>
                          )}

                        {j.result.ai_summary && (
                          <div className="mt-2 p-2 bg-white/5 rounded">
                            <div className="font-semibold">AI Summary:</div>
                            <div className="whitespace-pre-wrap text-sm">
                              {j.result.ai_summary}
                            </div>
                          </div>
                        )}

                        {!j.result.ai_summary && j.status === "done" && (
                          <div className="text-xs opacity-70 mt-1">
                            No AI summary available. Add OPENAI_API_KEY to backend .env to enable.
                          </div>
                        )}
                      </div>
                    )}

                    {j.error && (
                      <div className="text-red-400 mt-2">{j.error}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="page-bottom-space" />
        </section>
      </main>
    </div>
  );
}
