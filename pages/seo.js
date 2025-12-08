import { useState } from "react";
import axios from "axios";
import NavBar from "../components/NavBar";

export default function SEOAnalyzer() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeSEO = async (e) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setResult(null);

    try {
      const resp = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE}/api/seo`, {
        url,
        ai_rewrite: true,
      });
      setResult(resp.data);
    } catch (err) {
      console.error(err);
      alert("SEO analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen page-wrapper">
      <NavBar />

      <main className="max-w-5xl mx-auto py-8 px-4 space-y-6">
        
        {/* Title */}
        <h1 className="text-3xl font-bold">SEO Analyzer</h1>

        {/* Input Form */}
        <form onSubmit={analyzeSEO} className="card p-6 space-y-4">
          <input
            type="text"
            className="input w-full"
            placeholder="Enter a webpage URL (https://...)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />

          <button className="btn-primary w-full" disabled={loading}>
            {loading ? "Analyzing..." : "Analyze SEO"}
          </button>
        </form>

        {/* Results */}
        {result && (
          <div className="card p-6 space-y-4">

            <h2 className="text-xl font-bold">Results</h2>

            <div>
              <strong>Title:</strong>
              <p>{result.title || "N/A"}</p>
            </div>

            <div>
              <strong>Meta Description:</strong>
              <p>{result.meta_description || "N/A"}</p>
            </div>

            <div>
              <strong>Headings:</strong>
              <ul className="list-disc ml-6">
                {result.headings?.map((h, i) => (
                  <li key={i}>{h.tag.toUpperCase()}: {h.text}</li>
                ))}
              </ul>
            </div>

            <div>
              <strong>Top Keywords:</strong>
              <ul className="list-disc ml-6">
                {result.top_keywords?.map((k, i) => (
                  <li key={i}>
                    {k.keyword} — {k.count} times ({k.density}%)
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <strong>Readability Score:</strong>
              <p>Flesch Reading Ease: {result.readability?.flesch_reading_ease}</p>
              <p>Sentences: {result.readability?.sentences}</p>
              <p>Words: {result.readability?.words}</p>
              <p>Syllables: {result.readability?.syllables}</p>
            </div>

            <div>
              <strong>Suggestions:</strong>
              <ul className="list-disc ml-6">
                {result.suggestions?.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>

            {result.ai_rewrite && (
              <div>
                <strong>AI Rewrite:</strong>
                <p className="whitespace-pre-wrap">{result.ai_rewrite}</p>
              </div>
            )}

          </div>
        )}
      </main>
    </div>
  );
}
