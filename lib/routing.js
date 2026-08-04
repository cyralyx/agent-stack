'use strict';
// routing.js — layered intent routing (mission §11).
// Replace the fragile single-regex approach with:
//   1. explicit user selection
//   2. deterministic rules
//   3. capability matching
//   4. (optional) model-based classification
//   5. safe fallback
const platform = require('./platform');

// Deterministic rule: execution verbs → openclaw (hands), everything else → hermes (brain).
const EXECUTION_VERBS = /^(create|make|build|write|fix|install|run|start|stop|deploy|scan|gather|list|remove|delete|organize|sort|merge|push|commit|test|rebuild|uninstall|download|open|close|restart|configure|setup)\b/i;
const RESEARCH_VERBS = /^(research|summarize|explain|analyze|compare|review|plan|recommend|design|assess|evaluate|outline|what|why|how|describe|list reasons)\b/i;

function detectExecutionTask(text) {
  return EXECUTION_VERBS.test(text.trim());
}

function detectResearchTask(text) {
  return RESEARCH_VERBS.test(text.trim());
}

// Select target with structured output (mission §11).
function route(task, opts = {}) {
  const text = String(task || '').trim();
  const explicit = opts.agent; // explicit user selection (layer 1)

  let selected_target;
  let reason;
  let confidence;

  if (explicit === 'hermes' || explicit === 'openclaw') {
    selected_target = explicit;
    reason = 'explicit user selection';
    confidence = 1.0;
  } else if (detectExecutionTask(text)) {
    // execution → hands (OpenClaw), unless it's actually research-wrapped
    selected_target = 'openclaw';
    reason = 'detected execution verb (files/system mutation)';
    confidence = 0.85;
  } else if (detectResearchTask(text) || /[?]/ .test(text)) {
    selected_target = 'hermes';
    reason = 'research/planning question without system mutation';
    confidence = 0.9;
  } else {
    // safe fallback (layer 5): default to brain for anything ambiguous
    selected_target = 'hermes';
    reason = 'safe default: ambiguous task routed to brain';
    confidence = 0.6;
  }

  // alternatives
  const alternatives = selected_target === 'hermes' ? ['openclaw'] : ['hermes'];

  return {
    selected_target,
    reason,
    confidence,
    alternatives,
    required_permissions: selected_target === 'openclaw' && detectExecutionTask(text) ? ['process.execute'] : [],
  };
}

module.exports = { route, detectExecutionTask, detectResearchTask };
