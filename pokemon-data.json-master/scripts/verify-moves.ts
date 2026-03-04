import { readFileSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';
import type { Move } from '../types/moves.ts';

const repoRoot = resolve(import.meta.dir, '..');
const movesPath = join(repoRoot, 'moves.json');
const typesPath = join(repoRoot, 'types.json');
const outputPath = join(repoRoot, 'scripts/moves-validation.json');

const REQUIRED_MOVE_KEYS = ['id', 'name', 'type', 'category', 'pp', 'power', 'accuracy'] as const;
const REQUIRED_NAME_KEYS = ['english', 'japanese', 'french', 'chinese'] as const;

function readJson<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, 'utf-8'));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function validateMove(move: unknown, allowedTypes: Set<string>): string[] {
  const missingKeys: string[] = [];

  if (typeof move !== 'object' || move === null) {
    return REQUIRED_MOVE_KEYS.map(k => k);
  }

  const m = move as Record<string, unknown>;

  // Check top-level required keys
  for (const key of REQUIRED_MOVE_KEYS) {
    if (!(key in m)) {
      missingKeys.push(key);
    }
  }

  // Check if id exists and is valid
  if (!('id' in m) || !isNonEmptyString(m.id)) {
    if (!missingKeys.includes('id')) {
      missingKeys.push('id');
    }
  }

  // Check name object and its required keys
  if (!('name' in m) || !m.name || typeof m.name !== 'object' || m.name === null) {
    if (!missingKeys.includes('name')) {
      missingKeys.push('name');
    }
  } else {
    const name = m.name as Record<string, unknown>;
    for (const key of REQUIRED_NAME_KEYS) {
      if (!(key in name) || !isNonEmptyString(name[key])) {
        missingKeys.push(`name.${key}`);
      }
    }
  }

  // Check type
  if (!('type' in m) || !isNonEmptyString(m.type)) {
    if (!missingKeys.includes('type')) {
      missingKeys.push('type');
    }
  }

  // Check category
  if (!('category' in m) || !isNonEmptyString(m.category)) {
    if (!missingKeys.includes('category')) {
      missingKeys.push('category');
    }
  }

  // Check pp
  if (!('pp' in m) || !isNonEmptyString(m.pp)) {
    if (!missingKeys.includes('pp')) {
      missingKeys.push('pp');
    }
  }

  // Check power
  if (!('power' in m) || !isNonEmptyString(m.power)) {
    if (!missingKeys.includes('power')) {
      missingKeys.push('power');
    }
  }

  // Check accuracy
  if (!('accuracy' in m) || !isNonEmptyString(m.accuracy)) {
    if (!missingKeys.includes('accuracy')) {
      missingKeys.push('accuracy');
    }
  }

  return missingKeys;
}

interface Failure {
  id: string;
  name?: string;
  missingKeys: string[];
}

function main(): void {
  const moves = readJson<Move[]>(movesPath);
  const types = readJson<Array<{ english: string }>>(typesPath);
  const allowedTypes = new Set(types.map((t) => t.english));

  const failures: Failure[] = [];

  for (const move of moves) {
    const missingKeys = validateMove(move, allowedTypes);
    if (missingKeys.length > 0) {
      const moveName = typeof move === 'object' && move !== null && 'name' in move && 
        typeof move.name === 'object' && move.name !== null && 'english' in move.name &&
        typeof move.name.english === 'string' ? move.name.english : undefined;
      
      failures.push({
        id: typeof move === 'object' && move !== null && 'id' in move && typeof move.id === 'string' 
          ? move.id 
          : 'unknown',
        name: moveName,
        missingKeys,
      });
    }
  }

  // Write results to JSON file
  const results = {
    timestamp: new Date().toISOString(),
    totalMoves: moves.length,
    movesWithMissingKeys: failures.length,
    failures: failures,
  };

  writeFileSync(outputPath, JSON.stringify(results, null, 2), 'utf-8');

  if (failures.length === 0) {
    console.log(`OK: ${moves.length} moves validated`);
    console.log(`Results written to: ${outputPath}`);
    return;
  }

  console.log(`Found ${failures.length} move(s) with missing keys`);
  console.log(`Results written to: ${outputPath}\n`);
  
  // Also print summary to console
  for (const failure of failures) {
    console.log(`ID: ${failure.id}${failure.name ? ` (${failure.name})` : ''}`);
    console.log(`Missing keys: ${failure.missingKeys.join(', ')}\n`);
  }
  process.exitCode = 1;
}

main();
