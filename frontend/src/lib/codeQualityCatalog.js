/**
 * Code Analysis dashboard catalog — high-reasoning LLMHub models + issue taxonomy.
 */

/** Prefer high-reasoning / efficient models for deep code analysis. */
export const HIGH_REASONING_MODEL_PREFS = [
  'fable-5.1',
  'fable-5.1-thinking',
  'claude-fable-5-1-thinking-high',
  'claude-fable-5-1',
  'o3',
  'o3-mini',
  'o4-mini',
  'gpt-4.1',
  'gpt-4o',
  'gpt-4.1-mini'
];

export const ISSUE_FILTERS = [
  { id: 'error', label: 'Errors' },
  { id: 'bug', label: 'Bugs' },
  { id: 'fallacy', label: 'Logical fallacies' },
  { id: 'security', label: 'Security / vulns' },
  { id: 'memory', label: 'Memory / leaks' },
  { id: 'endpoint', label: 'Endpoints / auth' },
  { id: 'quality', label: 'SonarQube / quality' },
  { id: 'optimize', label: 'Optimization' }
];

/** Default issue tab when opening Code Analysis. */
export const DEFAULT_ISSUE_FILTER = 'error';

/**
 * @param {string[]} liveOptions
 * @returns {{ id: string, label: string, recommended: boolean }[]}
 */
export function buildReasoningModelOptions(liveOptions = []) {
  const live = Array.isArray(liveOptions) ? liveOptions : [];
  const lower = new Map(live.map((m) => [String(m).toLowerCase(), m]));
  /** @type {{ id: string, label: string, recommended: boolean }[]} */
  const out = [];
  const seen = new Set();

  for (const pref of HIGH_REASONING_MODEL_PREFS) {
    const match = lower.get(pref.toLowerCase()) || (live.includes(pref) ? pref : null);
    if (!match || seen.has(match)) continue;
    seen.add(match);
    const recommended = /fable|o3|o4/i.test(match);
    out.push({
      id: match,
      label: recommended ? `${match} · recommended` : match,
      recommended
    });
  }

  for (const m of live) {
    if (seen.has(m)) continue;
    seen.add(m);
    out.push({ id: m, label: m, recommended: false });
  }

  if (!out.length) {
    return HIGH_REASONING_MODEL_PREFS.slice(0, 6).map((id, i) => ({
      id,
      label: i === 0 ? `${id} · recommended` : id,
      recommended: i === 0
    }));
  }
  return out;
}

export const DEFAULT_QUALITY_REPORT = {
  model: 'fable-5.1',
  source: '',
  ran_at: null,
  summary: '',
  scorecards: {
    bugs: 0,
    logical_fallacies: 0,
    errors: 0,
    security_score: 0,
    quality_score: 0,
    vulnerability_count: 0,
    memory_risk_points: 0,
    open_endpoint_risks: 0,
    optimization_opportunities: 0
  },
  analyses: {
    static: 'idle',
    dynamic: 'idle',
    sonarqube: 'idle',
    memory_profile: 'idle',
    security_scan: 'idle',
    endpoint_auth: 'idle'
  },
  issues: [],
  recommendations: [
    {
      id: 'R0',
      title: 'Run analysis on a high-reasoning model',
      detail:
        'Use Fable 5.1 (or o3 / o4-mini) for better bug, fallacy, and security reasoning before merging.',
      category: 'quality'
    }
  ]
};
