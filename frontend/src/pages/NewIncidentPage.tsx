import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Loader2, AlertCircle, FileText, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export function NewIncidentPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [rawData, setRawData] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const incident = await api.createIncident({ title, description, raw_data: rawData || undefined });
      navigate(`/incidents/${incident.id}`);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Failed to create incident');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/incidents" className="btn btn-secondary p-2" aria-label="Back to incidents">
          <ArrowLeft className="w-5 h-5" aria-hidden="true" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">New Incident</h1>
          <p className="text-slate-500 mt-1">Create a new incident for analysis</p>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="card space-y-6" noValidate>
        <div className="card-header">
          <h2 className="text-lg font-semibold">Incident Details</h2>
        </div>
        <div className="card-body space-y-6">
          <div>
            <label htmlFor="title" className="label">Title <span className="text-red-500">*</span></label>
            <input
              id="title"
              type="text"
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief incident title (e.g., API latency spike in us-east-1)"
              required
              maxLength={255}
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="description" className="label">Description <span className="text-red-500">*</span></label>
            <textarea
              id="description"
              className="input min-h-[120px] resize-y"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what happened, symptoms, and any known context..."
              required
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="rawData" className="label">Raw Data (Optional)</label>
            <textarea
              id="rawData"
              className="input min-h-[200px] resize-y font-mono text-sm"
              value={rawData}
              onChange={(e) => setRawData(e.target.value)}
              placeholder="Paste logs, metrics, timeline events, or any raw incident data here. This will be used for AI analysis."
              disabled={loading}
            />
            <p className="mt-1 text-sm text-slate-500">
              JSON, plain text, or structured logs accepted. The AI will extract relevant information.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <Link to="/incidents" className="btn btn-secondary">
              Cancel
            </Link>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !title.trim() || !description.trim()}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
                  Creating...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" aria-hidden="true" />
                  Create Incident
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}