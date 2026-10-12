import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { 
  Incident, 
  TriageResult, 
  BlastAnalysis, 
  CommsTemplate, 
  Postmortem 
} from '../types/api';
import { 
  ArrowLeft, 
  AlertTriangle, 
  ShieldAlert, 
  Radio, 
  Mail, 
  FileText, 
  Loader2, 
  Bot
} from 'lucide-react';
import clsx from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  open: 'badge-open',
  in_progress: 'badge-in_progress',
  resolved: 'badge-resolved',
  closed: 'badge-closed',
};

const SEVERITY_COLORS: Record<string, string> = {
  SEV1: 'badge-sev1',
  SEV2: 'badge-sev2',
  SEV3: 'badge-sev3',
  SEV4: 'badge-sev4',
};

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const incidentId = parseInt(id || '0', 10);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Workflow states
  const [triage, setTriage] = useState<TriageResult | null>(null);
  const [blast, setBlast] = useState<BlastAnalysis | null>(null);
  const [comms, setComms] = useState<CommsTemplate | null>(null);
  const [postmortem, setPostmortem] = useState<Postmortem | null>(null);

  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const fetchIncident = async () => {
      if (!incidentId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await api.getIncident(incidentId);
        setIncident(data);
      } catch (err: unknown) {
        setError('Failed to load incident details');
      } finally {
        setLoading(false);
      }
    };
    fetchIncident();
  }, [incidentId]);

  const handleRunTriage = async (useLlm = false) => {
    setActionLoading('triage');
    setActionError(null);
    try {
      const res = await api.triageIncident(incidentId, useLlm);
      setTriage(res);
      // Refresh incident status/severity
      const updated = await api.getIncident(incidentId);
      setIncident(updated);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setActionError(axiosError.response?.data?.detail || 'Triage analysis failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunBlast = async (useLlm = false) => {
    setActionLoading('blast');
    setActionError(null);
    try {
      const res = await api.analyzeBlastRadius(incidentId, ['api', 'database', 'auth-service', 'worker-queue'], useLlm);
      setBlast(res);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setActionError(axiosError.response?.data?.detail || 'Blast radius analysis failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleGenerateComms = async (channel: string, phase: string, useLlm = false) => {
    setActionLoading(`comms-${channel}`);
    setActionError(null);
    try {
      const res = await api.generateComms(incidentId, channel, phase, useLlm);
      setComms(res);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setActionError(axiosError.response?.data?.detail || 'Communications generation failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleGeneratePostmortem = async (useLlm = false) => {
    setActionLoading('postmortem');
    setActionError(null);
    try {
      const res = await api.generatePostmortem(incidentId, useLlm);
      setPostmortem(res);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setActionError(axiosError.response?.data?.detail || 'Postmortem synthesis failed');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="space-y-4">
        <Link to="/incidents" className="btn btn-secondary inline-flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" /> Back to incidents
        </Link>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error || 'Incident not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link to="/incidents" className="text-slate-500 hover:text-slate-800" aria-label="Back">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-2xl font-bold text-slate-900">{incident.title}</h1>
            <span className={clsx('badge', STATUS_COLORS[incident.status])}>
              {incident.status.replace('_', ' ')}
            </span>
            {incident.severity && (
              <span className={clsx('badge', SEVERITY_COLORS[incident.severity])}>
                {incident.severity}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 ml-8">
            Created: {new Date(incident.created_at).toLocaleString()} • Last updated: {new Date(incident.updated_at).toLocaleString()}
          </p>
        </div>
      </div>

      {actionError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          {actionError}
        </div>
      )}

      {/* Incident Description & Raw Context */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-slate-900">Incident Context</h2>
        </div>
        <div className="card-body space-y-4">
          <p className="text-slate-700">{incident.description}</p>
          {incident.raw_data && (
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                Raw Log Stream
              </span>
              <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg text-xs overflow-x-auto font-mono">
                {incident.raw_data}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Workflows Navigation & Execution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Workflow 1: Severity Triage */}
        <div className="card flex flex-col justify-between">
          <div className="card-body space-y-4">
            <div className="flex items-center gap-3 text-blue-600">
              <ShieldAlert className="w-6 h-6" />
              <h3 className="font-semibold text-slate-900">1. Triage & Containment</h3>
            </div>
            <p className="text-sm text-slate-600">
              Deterministic rule-based severity ranking and prioritized containment runbook synthesis.
            </p>
            {triage && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="font-semibold">Severity:</span>
                  <span className={clsx('badge', SEVERITY_COLORS[triage.severity])}>{triage.severity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold">Confidence:</span>
                  <span>{Math.round(triage.confidence * 100)}%</span>
                </div>
                <div>
                  <span className="font-semibold block mb-1">Reasoning:</span>
                  <p className="text-slate-700">{triage.reasoning}</p>
                </div>
              </div>
            )}
          </div>
          <div className="card-footer bg-slate-50 p-4 border-t border-slate-100 flex gap-2">
            <button
              onClick={() => handleRunTriage(false)}
              disabled={actionLoading === 'triage'}
              className="btn btn-secondary text-xs flex-1"
            >
              {actionLoading === 'triage' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Run Triage'}
            </button>
            <button
              onClick={() => handleRunTriage(true)}
              disabled={actionLoading === 'triage'}
              className="btn btn-primary text-xs flex items-center gap-1"
              title="Run with LLM Copilot"
            >
              <Bot className="w-3.5 h-3.5" /> LLM
            </button>
          </div>
        </div>

        {/* Workflow 2: Blast Radius */}
        <div className="card flex flex-col justify-between">
          <div className="card-body space-y-4">
            <div className="flex items-center gap-3 text-orange-600">
              <Radio className="w-6 h-6" />
              <h3 className="font-semibold text-slate-900">2. Blast Radius Analysis</h3>
            </div>
            <p className="text-sm text-slate-600">
              Map affected upstream/downstream topologies, data corruption risks, and user cohorts.
            </p>
            {blast && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                <div>
                  <span className="font-semibold block mb-1">Affected Services:</span>
                  <div className="flex flex-wrap gap-1">
                    {blast.affected_services.map((svc, idx) => (
                      <span key={idx} className="badge bg-slate-200 text-slate-800">{svc}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="font-semibold block mb-1">Impact:</span>
                  <p className="text-slate-700 truncate">{blast.user_impact || blast.data_impact}</p>
                </div>
              </div>
            )}
          </div>
          <div className="card-footer bg-slate-50 p-4 border-t border-slate-100 flex gap-2">
            <button
              onClick={() => handleRunBlast(false)}
              disabled={actionLoading === 'blast'}
              className="btn btn-secondary text-xs flex-1"
            >
              {actionLoading === 'blast' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Analyze Blast'}
            </button>
            <button
              onClick={() => handleRunBlast(true)}
              disabled={actionLoading === 'blast'}
              className="btn btn-primary text-xs flex items-center gap-1"
            >
              <Bot className="w-3.5 h-3.5" /> LLM
            </button>
          </div>
        </div>

        {/* Workflow 3: Incident Comms */}
        <div className="card flex flex-col justify-between">
          <div className="card-body space-y-4">
            <div className="flex items-center gap-3 text-purple-600">
              <Mail className="w-6 h-6" />
              <h3 className="font-semibold text-slate-900">3. Comms Generation</h3>
            </div>
            <p className="text-sm text-slate-600">
              Draft status page incidents, Slack channel announcements, and stakeholder emails.
            </p>
            {comms && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                <span className="font-semibold uppercase">{comms.channel} • {comms.phase}</span>
                <p className="text-slate-700 whitespace-pre-wrap">{comms.content}</p>
              </div>
            )}
          </div>
          <div className="card-footer bg-slate-50 p-4 border-t border-slate-100 flex gap-2">
            <button
              onClick={() => handleGenerateComms('status', 'initial', false)}
              disabled={actionLoading?.startsWith('comms')}
              className="btn btn-secondary text-xs flex-1"
            >
              Draft Status
            </button>
            <button
              onClick={() => handleGenerateComms('slack', 'initial', false)}
              disabled={actionLoading?.startsWith('comms')}
              className="btn btn-secondary text-xs flex-1"
            >
              Draft Slack
            </button>
          </div>
        </div>
      </div>

      {/* Retrospective / Postmortem */}
      <div className="card">
        <div className="card-header flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-500" /> Postmortem Report
          </h2>
          <button
            onClick={() => handleGeneratePostmortem(false)}
            disabled={actionLoading === 'postmortem'}
            className="btn btn-secondary text-xs"
          >
            {actionLoading === 'postmortem' ? 'Generating...' : 'Synthesize Postmortem'}
          </button>
        </div>
        <div className="card-body">
          {postmortem ? (
            <div className="space-y-4 text-sm">
              <div>
                <h4 className="font-semibold text-slate-800">Summary</h4>
                <p className="text-slate-600 mt-1">{postmortem.summary}</p>
              </div>
              <div>
                <h4 className="font-semibold text-slate-800">Root Cause</h4>
                <p className="text-slate-600 mt-1">{postmortem.root_cause}</p>
              </div>
              <div>
                <h4 className="font-semibold text-slate-800">Timeline</h4>
                <p className="text-slate-600 mt-1 whitespace-pre-wrap font-mono text-xs bg-slate-50 p-3 rounded">
                  {postmortem.timeline}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">No postmortem generated yet for this incident.</p>
          )}
        </div>
      </div>
    </div>
  );
}
