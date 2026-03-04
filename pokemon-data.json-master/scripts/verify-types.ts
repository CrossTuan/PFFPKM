import { readFileSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';
import type { Type } from '../types/types.ts';

const repoRoot = resolve(import.meta.dir, '..');
const typesPath = join(repoRoot, 'types.json');
const outputPath = join(repoRoot, 'scripts/types-validation.json');

const REQUIRED_TYPE_KEYS = ['english', 'chinese', 'japanese', 'effective', 'ineffective', 'no_effect'] as const;

function readJson<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, 'utf-8'));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string');
}

function validateType(type: unknown): string[] {
  const missingKeys: string[] = [];

  if (typeof type !== 'object' || type === null) {
    return REQUIRED_TYPE_KEYS.map(k => k);
  }

  const t = type as Record<string, unknown>;

  // Check top-level required keys
  for (const key of REQUIRED_TYPE_KEYS) {
    if (!(key in t)) {
      missingKeys.push(key);
    }
  }

  // Check english
  if (!('english' in t) || !isNonEmptyString(t.english)) {
    if (!missingKeys.includes('english')) {
      missingKeys.push('english');
    }
  }

  // Check chinese
  if (!('chinese' in t) || !isNonEmptyString(t.chinese)) {
    if (!missingKeys.includes('chinese')) {
      missingKeys.push('chinese');
    }
  }

  // Check japanese
  if (!('japanese' in t) || !isNonEmptyString(t.japanese)) {
    if (!missingKeys.includes('japanese')) {
      missingKeys.push('japanese');
    }
  }

  // Check effective
  if (!('effective' in t) || !isStringArray(t.effective)) {
    if (!missingKeys.includes('effective')) {
      missingKeys.push('effective');
    }
  }

  // Check ineffective
  if (!('ineffective' in t) || !isStringArray(t.ineffective)) {
    if (!missingKeys.includes('ineffective')) {
      missingKeys.push('ineffective');
    }
  }

  // Check no_effect
  if (!('no_effect' in t) || !isStringArray(t.no_effect)) {
    if (!missingKeys.includes('no_effect')) {
      missingKeys.push('no_effect');
    }
  }

  return missingKeys;
}

interface Failure {
  name?: string;
  missingKeys: string[];
}

function main(): void {
  const types = readJson<Type[]>(typesPath);

  const failures: Failure[] = [];

  for (const type of types) {
    const missingKeys = validateType(type);
    if (missingKeys.length > 0) {
      failures.push({
        name: typeof type === 'object' && type !== null && 'english' in type &&
          typeof type.english === 'string' ? type.english : undefined,
        missingKeys,
      });
    }
  }

  // Write results to JSON file
  const results = {
    timestamp: new Date().toISOString(),
    totalTypes: types.length,
    typesWithMissingKeys: failures.length,
    failures: failures,
  };

  writeFileSync(outputPath, JSON.stringify(results, null, 2), 'utf-8');

  if (failures.length === 0) {
    console.log(`OK: ${types.length} types validated`);
    console.log(`Results written to: ${outputPath}`);
    return;
  }

  console.log(`Found ${failures.length} type(s) with missing keys`);
  console.log(`Results written to: ${outputPath}\n`);

  // Also print summary to console
  for (const failure of failures) {
    console.log(`${failure.name ? `Type: ${failure.name}` : 'Unknown type'}`);
    console.log(`Missing keys: ${failure.missingKeys.join(', ')}\n`);
  }
  process.exitCode = 1;
}

main();
