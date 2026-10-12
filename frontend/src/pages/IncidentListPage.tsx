import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Incident, IncidentStatus, SeverityLevel } from '../types/api';
import { IncidentStatus as StatusEnum, SeverityLevel as SevEnum } from '../types/api';
import { 
  Plus, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  Loader2,
  FileText
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

const statusOptions: { value: IncidentStatus | ''; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: StatusEnum.OPEN, label: 'Open' },
  { value: StatusEnum.IN_PROGRESS, label: 'In Progress' },
  { value: StatusEnum.RESOLVED, label: 'Resolved' },
  { value: StatusEnum.CLOSED, label: 'Closed' },
];

const severityOptions: { value: SeverityLevel | ''; label: string }[] = [
  { value: '', label: 'All severities' },
  { value: SevEnum.SEV1, label: 'SEV-1' },
  { value: SevEnum.SEV2, label: 'SEV-2' },
  { value: SevEnum.SEV3, label: 'SEV-3' },
  { value: SevEnum.SEV4, label: 'SEV-4' },
];

export function IncidentListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10);
  const status = searchParams.get('status') || '';
  const severity = searchParams.get('severity') || '';
  const search = searchParams.get('search') || '';

  useEffect(() => {
    const fetchIncidents = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listIncidents({
          page,
          page_size: pageSize,
          status: status || undefined,
          severity: severity || undefined,
        });
        setIncidents(res.items);
        setTotal(res.total);
      } catch (err) {
        setError('Failed to load incidents');
      } finally {
        setLoading(false);
      }
    };
    fetchIncidents();
  }, [page, pageSize, status, severity]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const params = new URLSearchParams(searchParams);
    params.set('search', e.target.value);
    params.set('page', '1');
    setSearchParams(params);
  };

  const handleFilterChange = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set('page', '1');
    setSearchParams(params);
  };

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(newPage));
    setSearchParams(params);
  };

  const totalPages = Math.ceil(total / pageSize);

  if (loading && incidents.length === 0) {
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
          <h1 className="text-2xl font-bold text-slate-900">Incidents</h1>
          <p className="text-slate-500 mt-1">Manage and track all incidents</p>
        </div>
        <Link to="/incidents/new" className="btn btn-primary">
          <Plus className="w-4 h-4" aria-hidden="true" />
          New Incident
        </Link>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-3">
          <FileText className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search incidents..."
                value={search}
                onChange={handleSearchChange}
                className="input pl-10"
                aria-label="Search incidents"
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <select
                value={status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="input w-auto"
                aria-label="Filter by status"
              >
                {statusOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <select
                value={severity}
                onChange={(e) => handleFilterChange('severity', e.target.value)}
                className="input w-auto"
                aria-label="Filter by severity"
              >
                {severityOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="card">
        <div className="card-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-sm text-slate-500">
            Showing {incidents.length} of {total} incident{total !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="card-body p-0">
          {incidents.length === 0 ? (
            <div className="empty-state py-12">
              <FileText className="w-12 h-12" aria-hidden="true" />
              <p className="text-slate-500">No incidents found</p>
              {search || status || severity ? (
                <button
                  onClick={() => {
                    const params = new URLSearchParams();
                    setSearchParams(params);
                  }}
                  className="btn btn-secondary mt-4"
                >
                  Clear filters
                </button>
              ) : (
                <Link to="/incidents/new" className="btn btn-primary mt-4">
                  <Plus className="w-4 h-4" aria-hidden="true" />
                  Create your first incident
                </Link>
              )}
            </div>
          ) : (
            <>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th className="w-12">Severity</th>
                      <th>Title</th>
                      <th className="w-32">Status</th>
                      <th className="w-48">Created</th>
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
                        <td className="font-medium text-slate-900 truncate max-w-xs">
                          <Link to={`/incidents/${incident.id}`} className="hover:text-blue-600">
                            {incident.title}
                          </Link>
                        </td>
                        <td>
                          <span className={clsx('badge', STATUS_COLORS[incident.status])}>
                            {incident.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="text-sm text-slate-500">
                          {new Date(incident.created_at).toLocaleDateString()}
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
                            <FileText className="w-4 h-4" aria-hidden="true" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
                  <p className="text-sm text-slate-500">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                      className="btn btn-secondary btn-sm"
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= totalPages}
                      className="btn btn-secondary btn-sm"
                      aria-label="Next page"
                    >
                      <ChevronRight className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}