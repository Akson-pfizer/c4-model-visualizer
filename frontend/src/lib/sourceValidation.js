const GITHUB_PATTERNS = [
  /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\/.*)?$/,
  /^git@github\.com:[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\.git)?$/,
  /^github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\/.*)?$/
];

const LOCAL_PATH_PATTERN =
  /^(\/[A-Za-z0-9_.\-/ ]+|~\/[A-Za-z0-9_.\-/ ]+|\.\.?\/[A-Za-z0-9_.\-/ ]+|[A-Za-z]:\\[A-Za-z0-9_.\-\\ ]+|[A-Za-z0-9_.-]+(\/[A-Za-z0-9_.\-/ ]*)*)$/;

export const DEFAULT_AGENT_ROSTER = [
  {
    agent_id: 'c4-manager',
    role: 'Manager Agent',
    summary:
      'Accepts local path or GitHub URL, clones/scans repository, and invokes Supervisor.'
  },
  {
    agent_id: 'c4-supervisor',
    role: 'Supervisor Agent',
    summary:
      'Coordinates all 4 layer subagents and links Context → Container → Component → Code as a hierarchy tree.'
  },
  {
    agent_id: 'subagent-context',
    layer: 'context',
    role: 'Context Specialist',
    summary: 'Extracts top-level actors, systems in scope, and external integrations.'
  },
  {
    agent_id: 'subagent-container',
    layer: 'container',
    role: 'Container Specialist',
    summary: 'Extracts deployable apps, services, and data stores linked to Context systems.'
  },
  {
    agent_id: 'subagent-component',
    layer: 'component',
    role: 'Component Specialist',
    summary: 'Extracts controllers, services, and modules linked to parent Containers.'
  },
  {
    agent_id: 'subagent-code',
    layer: 'code',
    role: 'Code Specialist',
    summary: 'Extracts classes, interfaces, and module exports linked to parent Components.'
  }
];

export function validateSource(raw, type) {
  const val = raw.trim();
  if (!val) {
    return {
      valid: false,
      message:
        type === 'local'
          ? 'Enter a local directory path (e.g. /Users/.../repo or ./project).'
          : 'Enter a GitHub repository URL (e.g. https://github.com/owner/repo).'
    };
  }

  const looksLikeUrl =
    /^https?:\/\//i.test(val) || /^git@/i.test(val) || /^github\.com\//i.test(val);

  if (type === 'local') {
    if (looksLikeUrl) {
      return {
        valid: false,
        message:
          'Invalid Local path: a GitHub/remote URL was entered while "Local" is selected.'
      };
    }
    if (/[<>:"|?*\0]/.test(val) || !LOCAL_PATH_PATTERN.test(val)) {
      return {
        valid: false,
        message:
          'Invalid Local path format. Use a valid filesystem path such as /Users/name/repo or ./folder.'
      };
    }
    return {
      valid: true,
      message: 'Valid local filesystem path format ✓'
    };
  }

  if (
    val.startsWith('/') ||
    val.startsWith('~/') ||
    val.startsWith('./') ||
    val.startsWith('../')
  ) {
    return {
      valid: false,
      message:
        'Invalid Github path: a local filesystem path was entered while "Github" is selected.'
    };
  }

  const matchesGithub = GITHUB_PATTERNS.some((re) => re.test(val));
  if (!matchesGithub) {
    return {
      valid: false,
      message:
        'Invalid Github path. Expected https://github.com/<owner>/<repo> or git@github.com:<owner>/<repo>.git.'
    };
  }

  return {
    valid: true,
    message: 'Valid GitHub repository path ✓'
  };
}
