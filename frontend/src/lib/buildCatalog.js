// Palette for the Build Repo tab, plus the generator that turns the current
// drawable diagram into a plain-language implementation plan for human approval.

export const SHAPES = [
  {
    id: 'person',
    name: 'Person',
    kind: 'Shape',
    summary: 'A human actor outside the software, such as a customer or an operator.'
  },
  {
    id: 'system',
    name: 'Software System',
    kind: 'Shape',
    summary: 'The in-scope system under design, shown as one box on the context diagram.'
  },
  {
    id: 'external-system',
    name: 'External System',
    kind: 'Shape',
    summary: 'A system outside the scope of this build, such as email or a mainframe.'
  },
  {
    id: 'container',
    name: 'Container',
    kind: 'Shape',
    summary: 'An application or data store that runs inside the system.'
  },
  {
    id: 'database',
    name: 'Database',
    kind: 'Shape',
    summary: 'A container that stores state, drawn so it is not mistaken for an app.'
  },
  {
    id: 'component',
    name: 'Component',
    kind: 'Shape',
    summary: 'A building block inside one container, used only where it adds detail.'
  },
  {
    id: 'boundary',
    name: 'Boundary',
    kind: 'Shape',
    summary: 'A labelled frame around the system or container being zoomed into.'
  }
];

export const ARROWS = [
  {
    id: 'uses',
    name: 'Uses',
    kind: 'Arrow',
    summary: 'A synchronous relationship. One element calls another and waits.'
  },
  {
    id: 'async',
    name: 'Asynchronous',
    kind: 'Arrow',
    summary: 'A message that is sent without waiting, such as email or an event.'
  },
  {
    id: 'bidirectional',
    name: 'Bidirectional',
    kind: 'Arrow',
    summary: 'Two elements that each initiate a call to the other.'
  },
  {
    id: 'dependency',
    name: 'Dependency',
    kind: 'Arrow',
    summary: 'A build or design dependency with no runtime call on this diagram.'
  }
];

const KIND_ROLE = {
  person: 'human user outside the software',
  system: 'core software system in scope',
  systemExternal: 'external system outside our build boundary',
  container: 'deployable application container',
  containerDb: 'persistent database container',
  component: 'internal module inside a container',
  codeInterface: 'code-level interface contract',
  codeClass: 'concrete implementation class',
  codeEnum: 'domain enumeration type'
};

function countWord(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function insideBoundary(node, boundary) {
  if (node.parentId === boundary.id) return true;
  const nw = node.width ?? 220;
  const nh = node.height ?? 150;
  const cx = node.position.x + nw / 2;
  const cy = node.position.y + nh / 2;
  const bx = boundary.position.x;
  const by = boundary.position.y;
  const bw = boundary.width ?? 380;
  const bh = boundary.height ?? 240;
  return cx >= bx && cx <= bx + bw && cy >= by && cy <= by + bh;
}

function describeRelationship(edge, byId) {
  const source = byId.get(edge.source)?.data?.name ?? edge.source;
  const target = byId.get(edge.target)?.data?.name ?? edge.target;
  const label = (edge.label || 'Uses').toLowerCase();

  if (label.includes('async')) {
    return `${source} sends asynchronous messages to ${target} without waiting for an immediate reply, so this path needs a queue, event topic, or background delivery retry.`;
  }
  if (label.includes('bidirection')) {
    return `${source} and ${target} call each other in both directions. Agree on the request contract for each direction and avoid circular startup dependencies.`;
  }
  if (label.includes('depend')) {
    return `${source} depends on ${target} at build or configuration time rather than making a live runtime request.`;
  }
  return `${source} calls ${target} synchronously (${edge.label || 'Uses'}). Define the request/response contract, timeout, and error handling between them.`;
}

export function buildArchitecturePlan(nodes, edges, layerTitle = 'Architecture') {
  const boundaries = nodes.filter((n) => n.type === 'c4Boundary');
  const elements = nodes.filter((n) => n.type === 'c4Node');
  const byId = new Map(elements.map((n) => [n.id, n]));

  const summary =
    elements.length === 0 && boundaries.length === 0
      ? `The ${layerTitle} layer work area is currently empty. Drag shapes and arrows onto the canvas, then click Plan again to generate an implementation plan for approval.`
      : `The ${layerTitle} layer contains ${countWord(elements.length, 'component')}${
          boundaries.length ? `, grouped across ${countWord(boundaries.length, 'boundary', 'boundaries')},` : ''
        } and ${countWord(edges.length, 'connection')}. Review the plain-language plan below and approve it when you are ready to proceed.`;

  const boundaryItems = boundaries.map((b) => {
    const members = elements.filter((el) => insideBoundary(el, b)).map((el) => el.data.name);
    if (members.length === 0) {
      return `${b.data.label}: an empty boundary frame ready to enclose the services or containers that belong to this scope.`;
    }
    return `${b.data.label}: encloses ${members.join(', ')} under a single ownership and deployment boundary.`;
  });

  const nameCounts = new Map();
  const componentItems = elements.map((el) => {
    const name = el.data.name;
    const seen = (nameCounts.get(name) ?? 0) + 1;
    nameCounts.set(name, seen);
    const title = seen > 1 ? `${name} #${seen}` : name;
    const role = KIND_ROLE[el.data.kind] ?? 'architecture element';
    const tech = el.data.technology ? ` (${el.data.technology})` : '';
    return `${title}${tech} — ${role}. ${el.data.description}`;
  });

  const relationshipItems = edges.map((edge) => describeRelationship(edge, byId));

  const steps = [];
  if (boundaries.length > 0) {
    steps.push(
      `Establish the ${countWord(boundaries.length, 'system boundary', 'system boundaries')} (${boundaries
        .map((b) => b.data.label)
        .join(', ')}) in repository structure, network rules, and deployment configuration.`
    );
  }
  const dataStores = elements.filter((el) => el.data.kind === 'containerDb');
  if (dataStores.length > 0) {
    steps.push(
      `Provision the ${countWord(dataStores.length, 'data store')} (${dataStores
        .map((d) => d.data.name)
        .join(', ')}) first, along with schema migrations, credentials, and backup policy.`
    );
  }
  const coreServices = elements.filter((el) =>
    ['system', 'container', 'component', 'codeInterface', 'codeClass', 'codeEnum'].includes(el.data.kind)
  );
  if (coreServices.length > 0) {
    steps.push(
      `Implement and deploy the in-scope ${countWord(coreServices.length, 'service')} (${coreServices
        .map((s) => s.data.name)
        .join(', ')}) with health checks and structured logging.`
    );
  }
  const externals = elements.filter((el) =>
    ['person', 'systemExternal'].includes(el.data.kind)
  );
  if (externals.length > 0) {
    steps.push(
      `Configure access and integration adapters for ${externals.map((e) => e.data.name).join(', ')} so external boundaries stay isolated from internal domain code.`
    );
  }
  if (edges.length > 0) {
    steps.push(
      `Wire the ${countWord(edges.length, 'connection')} shown on the diagram, verifying authentication, timeouts, and fallback behavior end to end.`
    );
  }

  return {
    summary,
    componentCount: elements.length,
    boundaryCount: boundaries.length,
    edgeCount: edges.length,
    boundaryItems,
    componentItems,
    relationshipItems,
    steps
  };
}
