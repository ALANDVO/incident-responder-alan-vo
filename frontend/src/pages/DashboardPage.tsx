import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Incident, HealthResponse } from '../types/api';
import { 
  FileText, 
  Plus, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  ExternalLink,
  Loader2
} from 'lucide-react';
import clsx from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  open: 'badge-open',
  in_progress: 'badge-in_progress',
  resolved: 'badge-resolved',
  closed: 'badge-closed',
};

const SEVERITY_ICONS: Record<string, string> = {
  SEV1: 'sev1-icon',
  SEV2: 'sev2-icon',
  SEV3: 'sev3-icon',
  SEV4: 'sev4-icon',
};

export function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [incidentsRes, healthRes] = await Promise.all([
          api.listIncidents({ page_size: 5 }),
          api.healthCheck(),
        ]);
        setIncidents(incidentsRes.items);
        setHealth(healthRes);
      } catch (err) {
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const stats = {
    total: incidents.length,
    open: incidents.filter(i => i.status === 'open').length,
    inProgress: incidents.filter(i => i.status === 'in_progress').length,
    resolved: incidents.filter(i => i.status === 'resolved').length,
    sev1: incidents.filter(i => i.severity === 'SEV1').length,
    sev2: incidents.filter(i => i.severity === 'SEV2').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1">Overview of recent incidents and system health</p>
        </div>
        <Link to="/incidents/new" className="btn btn-primary">
          <Plus className="w-4 h-4" aria-hidden="true" />
          New Incident
        </Link>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          title="Total Incidents"
          value={stats.total}
          icon={FileText}
          color="text-blue-600 bg-blue-100"
        />
        <StatCard
          title="Open"
          value={stats.open}
          icon={AlertTriangle}
          color="text-red-600 bg-red-100"
        />
        <StatCard
          title="In Progress"
          value={stats.inProgress}
          icon={Clock}
          color="text-orange-600 bg-orange-100"
        />
        <StatCard
          title="Resolved"
          value={stats.resolved}
          icon={CheckCircle}
          color="text-green-600 bg-green-100"
        />
        <StatCard
          title="SEV-1"
          value={stats.sev1}
          icon={AlertTriangle}
          color="text-red-700 bg-red-100"
        />
        <StatCard
          title="SEV-2"
          value={stats.sev2}
          icon={TrendingUp}
          color="text-orange-700 bg-orange-100"
        />
      </div>

      {/* System Health */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold">System Health</h2>
        </div>
        <div className="card-body">
          <div className="flex flex-wrap items-center gap-4">
            <div className={clsx('flex items-center gap-2 px-3 py-1 rounded-full', health?.status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
              <span className={clsx('w-2 h-2 rounded-full', health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500')} aria-hidden="true" />
              <span className="text-sm font-medium">{health?.status || 'unknown'}</span>
            </div>
            <div className="text-sm text-slate-500">Version: {health?.version || 'unknown'}</div>
            <div className={clsx('flex items-center gap-1 px-3 py-1 rounded-full', health?.database === 'connected' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
              <span className={clsx('w-2 h-2 rounded-full', health?.database === 'connected' ? 'bg-green-500' : 'bg-red-500')} aria-hidden="true" />
              <span className="text-sm font-medium">Database: {health?.database || 'unknown'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Incidents */}
      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-lg font-semibold">Recent Incidents</h2>
          <Link to="/incidents" className="text-sm text-blue-600 hover:text-blue-500 font-medium">
            View all <ExternalLink className="w-3.5 h-3.5 ml-1" aria-hidden="true" />
          </Link>
        </div>
        <div className="card-body p-0">
          {incidents.length === 0 ? (
            <div className="empty-state py-12">
              <FileText className="w-12 h-12" aria-hidden="true" />
              <p className="text-slate-500">No incidents yet</p>
              <Link to="/incidents/new" className="btn btn-primary mt-4">
                <Plus className="w-4 h-4" aria-hidden="true" />
                Create your first incident
              </Link>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th className="w-12">Severity</th>
                    <th>Title</th>
                    <th className="w-32">Status</th>
                    <th className="w-48">Updated</th>
                    <th className="w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id}>
                      <td>
                        <span className={clsx('severity-icon', SEVERITY_ICONS[incident.severity || 'SEV3'])}>
                          {incident.severity?.slice(-1) || '?'}
                        </span>
                      </td>
                      <td className="font-medium text-slate-900 truncate max-w-xs">{incident.title}</td>
                      <td>
                        <span className={clsx('badge', STATUS_COLORS[incident.status])}>
                          {incident.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="text-sm text-slate-500">
                        {new Date(incident.updated_at).toLocaleDateString()}
                      </td>
                      <td>
                        <Link
                          to={`/incidents/${incident.id}`}
                          className="text-slate-400 hover:text-blue-600"
                          aria-label={`View incident ${incident.title}`}
                        >
                          <ExternalLink className="w-4 h-4" aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
        </div>
        <div className={clsx('p-2 rounded-lg', color)}>
          <Icon className="w-5 h-5" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}