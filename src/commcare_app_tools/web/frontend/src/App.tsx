import { useState, useEffect } from 'react';
import { ConfigWizard } from './components/ConfigWizard';
import type { TestConfig, TestConfigCreate, TerminalStatus } from './types';
import * as api from './api';

type View = 'list' | 'wizard' | 'run-command' | 'downloading';

function App() {
  const [view, setView] = useState<View>('list');
  const [configs, setConfigs] = useState<TestConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<TestConfig | null>(null);
  const [terminalStatus, setTerminalStatus] = useState<TerminalStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<string>('');
  const [runCommand, setRunCommand] = useState<string>('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [configsData, statusData] = await Promise.all([
        api.listTestConfigs(),
        api.getTerminalStatus(),
      ]);
      setConfigs(configsData);
      setTerminalStatus(statusData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateConfig(config: TestConfigCreate) {
    try {
      const newConfig = await api.createTestConfig(config);
      setConfigs([...configs, newConfig]);
      setView('list');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create config');
    }
  }

  async function handleDeleteConfig(id: string) {
    if (!confirm('Delete this configuration?')) return;
    try {
      await api.deleteTestConfig(id);
      setConfigs(configs.filter((c) => c.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete config');
    }
  }

  async function handleRunConfig(config: TestConfig) {
    setSelectedConfig(config);
    setError(null);
    setCopied(false);
    setView('downloading');

    try {
      // Check if app is already downloaded
      setDownloadProgress('Checking app status...');
      const appStatus = await api.getAppDownloadStatus(config.domain, config.app_id);

      if (!appStatus.downloaded) {
        setDownloadProgress(`Downloading app: ${config.app_name}...`);
        await api.downloadApp(config.domain, config.app_id);
        setDownloadProgress(`Downloaded ${config.app_name}`);
      } else {
        setDownloadProgress(`App already downloaded: ${config.app_name}`);
      }

      // Small delay so user can see the status
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Get the run command from the API
      setDownloadProgress('Generating run command...');
      const cmdResult = await api.getRunCommand(config.domain, config.app_id, config.user_id);
      setRunCommand(cmdResult.command);

      setView('run-command');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to prepare for run');
      setView('list');
    }
  }

  async function handleCopyCommand() {
    try {
      await navigator.clipboard.writeText(runCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      setError('Failed to copy to clipboard');
    }
  }

  const styles = {
    container: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      minHeight: '100vh',
      backgroundColor: '#fafafa',
    },
    header: {
      backgroundColor: '#1976d2',
      color: 'white',
      padding: '16px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    title: {
      margin: 0,
      fontSize: '20px',
      fontWeight: 500,
    },
    content: {
      padding: '24px',
      maxWidth: '1000px',
      margin: '0 auto',
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
      padding: '20px',
      marginBottom: '16px',
    },
    button: {
      padding: '8px 16px',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '14px',
    },
    primaryButton: {
      backgroundColor: '#1976d2',
      color: 'white',
    },
    secondaryButton: {
      backgroundColor: '#e0e0e0',
      color: '#333',
    },
    dangerButton: {
      backgroundColor: '#f44336',
      color: 'white',
    },
    statusBadge: {
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '12px',
      fontWeight: 500,
    },
    terminalContainer: {
      height: 'calc(100vh - 64px)',
    },
  };

  if (view === 'downloading' && selectedConfig) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>Preparing: {selectedConfig.name}</h1>
        </div>
        <div style={styles.content}>
          <div style={styles.card}>
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  border: '4px solid #e0e0e0',
                  borderTopColor: '#1976d2',
                  borderRadius: '50%',
                  margin: '0 auto 20px',
                  animation: 'spin 1s linear infinite',
                }}
              />
              <style>
                {`@keyframes spin { to { transform: rotate(360deg); } }`}
              </style>
              <p style={{ fontSize: '16px', color: '#333' }}>{downloadProgress}</p>
              <button
                style={{ ...styles.button, ...styles.secondaryButton, marginTop: '20px' }}
                onClick={() => {
                  setSelectedConfig(null);
                  setView('list');
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (view === 'run-command' && selectedConfig) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>Run: {selectedConfig.name}</h1>
          <button
            style={{ ...styles.button, ...styles.secondaryButton }}
            onClick={() => {
              setSelectedConfig(null);
              setView('list');
            }}
          >
            Back to List
          </button>
        </div>
        <div style={styles.content}>
          <div style={styles.card}>
            <h3 style={{ margin: '0 0 16px 0' }}>Copy this command to your terminal:</h3>
            <div
              style={{
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
                padding: '16px',
                borderRadius: '6px',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                fontSize: '13px',
                lineHeight: '1.5',
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {runCommand}
            </div>
            <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
              <button
                style={{
                  ...styles.button,
                  ...styles.primaryButton,
                  padding: '12px 24px',
                  fontSize: '16px',
                }}
                onClick={handleCopyCommand}
              >
                {copied ? 'Copied!' : 'Copy Command'}
              </button>
            </div>
            <p style={{ marginTop: '16px', color: '#666', fontSize: '14px' }}>
              Paste this command into PowerShell or your terminal to run the CommCare form.
            </p>
          </div>

          <div style={styles.card}>
            <h4 style={{ margin: '0 0 12px 0' }}>Configuration Details</h4>
            <table style={{ fontSize: '14px', color: '#666' }}>
              <tbody>
                <tr><td style={{ paddingRight: '16px' }}>Domain:</td><td>{selectedConfig.domain}</td></tr>
                <tr><td style={{ paddingRight: '16px' }}>App:</td><td>{selectedConfig.app_name}</td></tr>
                <tr><td style={{ paddingRight: '16px' }}>User:</td><td>{selectedConfig.username || 'Demo user'}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  if (view === 'wizard') {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>Create Test Configuration</h1>
        </div>
        <div style={styles.content}>
          <ConfigWizard
            onComplete={handleCreateConfig}
            onCancel={() => setView('list')}
          />
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>CommCare App Tools</h1>
        <button
          style={{ ...styles.button, ...styles.primaryButton }}
          onClick={() => setView('wizard')}
        >
          + New Configuration
        </button>
      </div>

      <div style={styles.content}>
        {/* Status card */}
        <div style={styles.card}>
          <h3 style={{ margin: '0 0 12px 0' }}>System Status</h3>
          {terminalStatus ? (
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div>
                <span
                  style={{
                    ...styles.statusBadge,
                    backgroundColor: terminalStatus.java.found ? '#e8f5e9' : '#ffebee',
                    color: terminalStatus.java.found ? '#2e7d32' : '#c62828',
                  }}
                >
                  Java: {terminalStatus.java.found ? 'OK' : 'Not Found'}
                </span>
              </div>
              <div>
                <span
                  style={{
                    ...styles.statusBadge,
                    backgroundColor: terminalStatus.cli_jar.built ? '#e8f5e9' : '#ffebee',
                    color: terminalStatus.cli_jar.built ? '#2e7d32' : '#c62828',
                  }}
                >
                  CLI JAR: {terminalStatus.cli_jar.built ? 'Built' : 'Not Built'}
                </span>
              </div>
              <div>
                <span
                  style={{
                    ...styles.statusBadge,
                    backgroundColor: terminalStatus.ready ? '#e8f5e9' : '#fff3e0',
                    color: terminalStatus.ready ? '#2e7d32' : '#e65100',
                  }}
                >
                  {terminalStatus.ready ? 'Ready to Run' : 'Setup Required'}
                </span>
              </div>
            </div>
          ) : loading ? (
            <p>Loading...</p>
          ) : (
            <p style={{ color: '#c62828' }}>Failed to check status</p>
          )}
          {!terminalStatus?.ready && (
            <p style={{ marginTop: '12px', color: '#666', fontSize: '14px' }}>
              Run <code style={{ backgroundColor: '#f5f5f5', padding: '2px 6px', borderRadius: '4px' }}>cc cli build</code> to build the CommCare CLI.
            </p>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div style={{ ...styles.card, backgroundColor: '#ffebee', color: '#c62828' }}>
            {error}
            <button
              style={{ ...styles.button, ...styles.secondaryButton, marginLeft: '12px' }}
              onClick={() => setError(null)}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Configs list */}
        <div style={styles.card}>
          <h3 style={{ margin: '0 0 16px 0' }}>Test Configurations</h3>

          {loading ? (
            <p>Loading configurations...</p>
          ) : configs.length === 0 ? (
            <p style={{ color: '#666' }}>
              No configurations yet. Click "New Configuration" to create one.
            </p>
          ) : (
            <div>
              {configs.map((config) => (
                <div
                  key={config.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px',
                    borderBottom: '1px solid #eee',
                  }}
                >
                  <div>
                    <strong>{config.name}</strong>
                    <div style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>
                      {config.domain} / {config.app_name} / {config.username}
                      {config.case_type && ` / ${config.case_type}`}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      style={{ ...styles.button, ...styles.primaryButton }}
                      onClick={() => handleRunConfig(config)}
                      disabled={!terminalStatus?.ready}
                    >
                      Run
                    </button>
                    <button
                      style={{ ...styles.button, ...styles.dangerButton }}
                      onClick={() => handleDeleteConfig(config.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
