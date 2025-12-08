import NavBar from "../components/NavBar";
import axios from "axios";
import { useEffect, useState } from "react";

export default function Dashboard(){
  const [jobs, setJobs] = useState([]);

  useEffect(()=>{ fetchJobs(); }, []);

  const fetchJobs = async () => {
    try {
      const resp = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE}/api/jobs`);
      setJobs(resp.data);
    } catch (err) { console.error(err); }
  };

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="max-w-5xl mx-auto py-8 px-4">
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <div className="grid grid-cols-1 gap-4">
          {jobs.map(j => (
            <div key={j.id} className="card p-4 flex justify-between">
              <div>
                <div className="font-semibold">{j.url}</div>
                <div className="text-sm opacity-80">ID: {j.id} • {j.status}</div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
