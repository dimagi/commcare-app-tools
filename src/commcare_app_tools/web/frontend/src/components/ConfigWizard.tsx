import { useState, useEffect } from 'react';
import type { DomainInfo, AppInfo, UserInfo, CaseInfo, TestConfigCreate } from '../types';
import * as api from '../api';

interface ConfigWizardProps {
  onComplete: (config: TestConfigCreate) => void;
  onCancel: () => void;
}

type Step = 'domain' | 'app' | 'user' | 'case' | 'review';

export function ConfigWizard({ onComplete, onCancel }: ConfigWizardProps) {
  const [step, setStep] = useState<Step>('domain');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data lists
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [caseTypes, setCaseTypes] = useState<string[]>([]);
  const [cases, setCases] = useState<CaseInfo[]>([]);

  // Selected values
  const [selectedDomain, setSelectedDomain] = useState<DomainInfo | null>(null);
  const [selectedApp, setSelectedApp] = useState<AppInfo | null>(null);
  const [selectedUser, setSelectedUser] = useState<UserInfo | null>(null);
  const [selectedCaseType, setSelectedCaseType] = useState<string>('');
  const [selectedCase, setSelectedCase] = useState<CaseInfo | null>(null);
  const [configName, setConfigName] = useState('');

  // Load domains on mount
  useEffect(() => {
    loadDomains();
  }, []);

  async function loadDomains() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDomains();
      setDomains(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load domains');
    } finally {
      setLoading(false);
    }
  }

  async function loadApps(domain: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listApps(domain);
      setApps(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load apps');
    } finally {
      setLoading(false);
    }
  }

  async function loadUsers(domain: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listUsers(domain);
      setUsers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }

  async function loadCaseTypes(domain: string) {
    try {
      const data = await api.listCaseTypes(domain);
      setCaseTypes(data);
    } catch (e) {
      console.error('Failed to load case types:', e);
    }
  }

  async function loadCases(domain: string, caseType: string) {
    setLoading(true);
    try {
      const data = await api.listCases(domain, caseType);
      setCases(data);
    } catch (e) {
      console.error('Failed to load cases:', e);
    } finally {
      setLoading(false);
    }
  }

  function handleDomainSelect(domain: DomainInfo) {
    setSelectedDomain(domain);
    setSelectedApp(null);
    setSelectedUser(null);
    setSelectedCase(null);
    loadApps(domain.domain);
    loadUsers(domain.domain);
    loadCaseTypes(domain.domain);
    setStep('app');
  }

  function handleAppSelect(app: AppInfo) {
    setSelectedApp(app);
    setStep('user');
  }

  function handleUserSelect(user: UserInfo) {
    setSelectedUser(user);
    setStep('case');
  }

  function handleCaseTypeSelect(caseType: string) {
    setSelectedCaseType(caseType);
    if (caseType && selectedDomain) {
      loadCases(selectedDomain.domain, caseType);
    } else {
      setCases([]);
    }
  }

  function handleSubmit() {
    if (!selectedDomain || !selectedApp || !selectedUser) return;

    const config: TestConfigCreate = {
      name: configName || `${selectedApp.name} - ${selectedUser.username}`,
      domain: selectedDomain.domain,
      app_id: selectedApp.id,
      app_name: selectedApp.name,
      user_id: selectedUser.id,
      username: selectedUser.username,
      case_type: selectedCaseType || undefined,
      case_id: selectedCase?.case_id,
    };

    onComplete(config);
  }

  const stepStyles = {
    container: {
      padding: '20px',
      maxWidth: '600px',
      margin: '0 auto',
    },
    header: {
      marginBottom: '20px',
    },
    list: {
      listStyle: 'none',
      padding: 0,
      margin: 0,
    },
    listItem: {
      padding: '12px 16px',
      margin: '8px 0',
      backgroundColor: '#f5f5f5',
      borderRadius: '4px',
      cursor: 'pointer',
      border: '2px solid transparent',
    },
    listItemHover: {
      backgroundColor: '#e3f2fd',
      borderColor: '#2196f3',
    },
    button: {
      padding: '10px 20px',
      margin: '4px',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
    },
    primaryButton: {
      backgroundColor: '#2196f3',
      color: 'white',
    },
    secondaryButton: {
      backgroundColor: '#e0e0e0',
      color: '#333',
    },
    select: {
      width: '100%',
      padding: '10px',
      marginBottom: '10px',
      borderRadius: '4px',
      border: '1px solid #ccc',
    },
    input: {
      width: '100%',
      padding: '10px',
      marginBottom: '10px',
      borderRadius: '4px',
      border: '1px solid #ccc',
      boxSizing: 'border-box' as const,
    },
    reviewItem: {
      padding: '8px 0',
      borderBottom: '1px solid #eee',
    },
  };

  if (loading) {
    return (
      <div style={stepStyles.container}>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={stepStyles.container}>
        <p style={{ color: 'red' }}>{error}</p>
        <button
          style={{ ...stepStyles.button, ...stepStyles.secondaryButton }}
          onClick={() => setError(null)}
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div style={stepStyles.container}>
      {/* Progress indicator */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '8px' }}>
        {(['domain', 'app', 'user', 'case', 'review'] as Step[]).map((s, i) => (
          <div
            key={s}
            style={{
              flex: 1,
              height: '4px',
              backgroundColor: i <= ['domain', 'app', 'user', 'case', 'review'].indexOf(step) ? '#2196f3' : '#e0e0e0',
              borderRadius: '2px',
            }}
          />
        ))}
      </div>

      {step === 'domain' && (
        <>
          <h2 style={stepStyles.header}>Select Domain</h2>
          <ul style={stepStyles.list}>
            {domains.map((domain) => (
              <li
                key={domain.domain}
                style={stepStyles.listItem}
                onClick={() => handleDomainSelect(domain)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e3f2fd';
                  e.currentTarget.style.borderColor = '#2196f3';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f5f5f5';
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <strong>{domain.name}</strong>
                <br />
                <small style={{ color: '#666' }}>{domain.domain}</small>
              </li>
            ))}
          </ul>
          <button
            style={{ ...stepStyles.button, ...stepStyles.secondaryButton, marginTop: '20px' }}
            onClick={onCancel}
          >
            Cancel
          </button>
        </>
      )}

      {step === 'app' && (
        <>
          <h2 style={stepStyles.header}>Select Application</h2>
          <p style={{ color: '#666', marginBottom: '16px' }}>
            Domain: <strong>{selectedDomain?.name}</strong>
          </p>
          <ul style={stepStyles.list}>
            {apps.map((app) => (
              <li
                key={app.id}
                style={stepStyles.listItem}
                onClick={() => handleAppSelect(app)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e3f2fd';
                  e.currentTarget.style.borderColor = '#2196f3';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f5f5f5';
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <strong>{app.name}</strong>
                {app.version && <small style={{ marginLeft: '8px', color: '#666' }}>v{app.version}</small>}
              </li>
            ))}
          </ul>
          <div style={{ marginTop: '20px' }}>
            <button
              style={{ ...stepStyles.button, ...stepStyles.secondaryButton }}
              onClick={() => setStep('domain')}
            >
              Back
            </button>
          </div>
        </>
      )}

      {step === 'user' && (
        <>
          <h2 style={stepStyles.header}>Select User</h2>
          <p style={{ color: '#666', marginBottom: '16px' }}>
            App: <strong>{selectedApp?.name}</strong>
          </p>
          <ul style={stepStyles.list}>
            {users.map((user) => (
              <li
                key={user.id}
                style={stepStyles.listItem}
                onClick={() => handleUserSelect(user)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e3f2fd';
                  e.currentTarget.style.borderColor = '#2196f3';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f5f5f5';
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <strong>{user.username}</strong>
                {(user.first_name || user.last_name) && (
                  <small style={{ marginLeft: '8px', color: '#666' }}>
                    ({user.first_name} {user.last_name})
                  </small>
                )}
              </li>
            ))}
          </ul>
          <div style={{ marginTop: '20px' }}>
            <button
              style={{ ...stepStyles.button, ...stepStyles.secondaryButton }}
              onClick={() => setStep('app')}
            >
              Back
            </button>
          </div>
        </>
      )}

      {step === 'case' && (
        <>
          <h2 style={stepStyles.header}>Select Case (Optional)</h2>
          <p style={{ color: '#666', marginBottom: '16px' }}>
            User: <strong>{selectedUser?.username}</strong>
          </p>

          <select
            style={stepStyles.select}
            value={selectedCaseType}
            onChange={(e) => handleCaseTypeSelect(e.target.value)}
          >
            <option value="">-- No case needed --</option>
            {caseTypes.map((ct) => (
              <option key={ct} value={ct}>{ct}</option>
            ))}
          </select>

          {selectedCaseType && (
            <ul style={stepStyles.list}>
              {cases.map((c) => (
                <li
                  key={c.case_id}
                  style={{
                    ...stepStyles.listItem,
                    borderColor: selectedCase?.case_id === c.case_id ? '#2196f3' : 'transparent',
                  }}
                  onClick={() => setSelectedCase(c)}
                >
                  <strong>{c.name || c.case_id}</strong>
                  <br />
                  <small style={{ color: '#666' }}>{c.case_id}</small>
                </li>
              ))}
            </ul>
          )}

          <div style={{ marginTop: '20px' }}>
            <button
              style={{ ...stepStyles.button, ...stepStyles.secondaryButton }}
              onClick={() => setStep('user')}
            >
              Back
            </button>
            <button
              style={{ ...stepStyles.button, ...stepStyles.primaryButton }}
              onClick={() => setStep('review')}
            >
              {selectedCaseType ? 'Next' : 'Skip'}
            </button>
          </div>
        </>
      )}

      {step === 'review' && (
        <>
          <h2 style={stepStyles.header}>Review Configuration</h2>

          <input
            type="text"
            placeholder="Configuration name (optional)"
            style={stepStyles.input}
            value={configName}
            onChange={(e) => setConfigName(e.target.value)}
          />

          <div style={{ backgroundColor: '#f5f5f5', padding: '16px', borderRadius: '4px' }}>
            <div style={stepStyles.reviewItem}>
              <small style={{ color: '#666' }}>Domain</small>
              <div><strong>{selectedDomain?.name}</strong></div>
            </div>
            <div style={stepStyles.reviewItem}>
              <small style={{ color: '#666' }}>Application</small>
              <div><strong>{selectedApp?.name}</strong></div>
            </div>
            <div style={stepStyles.reviewItem}>
              <small style={{ color: '#666' }}>User</small>
              <div><strong>{selectedUser?.username}</strong></div>
            </div>
            {selectedCaseType && (
              <div style={stepStyles.reviewItem}>
                <small style={{ color: '#666' }}>Case</small>
                <div>
                  <strong>{selectedCase?.name || selectedCase?.case_id || 'None selected'}</strong>
                  <small style={{ marginLeft: '8px', color: '#666' }}>({selectedCaseType})</small>
                </div>
              </div>
            )}
          </div>

          <div style={{ marginTop: '20px' }}>
            <button
              style={{ ...stepStyles.button, ...stepStyles.secondaryButton }}
              onClick={() => setStep('case')}
            >
              Back
            </button>
            <button
              style={{ ...stepStyles.button, ...stepStyles.primaryButton }}
              onClick={handleSubmit}
            >
              Save Configuration
            </button>
          </div>
        </>
      )}
    </div>
  );
}
