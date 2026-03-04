import { readFileSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';
import type { Item } from '../types/items.ts';

const repoRoot = resolve(import.meta.dir, '..');
const itemsPath = join(repoRoot, 'items.json');
const outputPath = join(repoRoot, 'scripts/items-validation.json');

const REQUIRED_ITEM_KEYS = ['id', 'name', 'type', 'description'] as const;
const REQUIRED_NAME_KEYS = ['english', 'japanese', 'chinese'] as const;

function readJson<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, 'utf-8'));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value);
}

function validateItem(item: unknown): string[] {
  const missingKeys: string[] = [];

  if (typeof item !== 'object' || item === null) {
    return REQUIRED_ITEM_KEYS.map(k => k);
  }

  const i = item as Record<string, unknown>;

  // Check top-level required keys
  for (const key of REQUIRED_ITEM_KEYS) {
    if (!(key in i)) {
      missingKeys.push(key);
    }
  }

  // Check id
  if (!('id' in i) || !isNumber(i.id)) {
    if (!missingKeys.includes('id')) {
      missingKeys.push('id');
    }
  }

  // Check name object and its required keys
  if (!('name' in i) || !i.name || typeof i.name !== 'object' || i.name === null) {
    if (!missingKeys.includes('name')) {
      missingKeys.push('name');
    }
  } else {
    const name = i.name as Record<string, unknown>;
    for (const key of REQUIRED_NAME_KEYS) {
      if (!(key in name) || !isNonEmptyString(name[key])) {
        missingKeys.push(`name.${key}`);
      }
    }
  }

  // Check type
  if (!('type' in i) || !isNonEmptyString(i.type)) {
    if (!missingKeys.includes('type')) {
      missingKeys.push('type');
    }
  }

  // Check description
  if (!('description' in i) || !isNonEmptyString(i.description)) {
    if (!missingKeys.includes('description')) {
      missingKeys.push('description');
    }
  }

  return missingKeys;
}

interface Failure {
  id: number | string;
  name?: string;
  missingKeys: string[];
}

function main(): void {
  const items = readJson<Item[]>(itemsPath);

  const failures: Failure[] = [];

  for (const item of items) {
    const missingKeys = validateItem(item);
    if (missingKeys.length > 0) {
      const itemName = typeof item === 'object' && item !== null && 'name' in item &&
        typeof item.name === 'object' && item.name !== null && 'english' in item.name &&
        typeof item.name.english === 'string' ? item.name.english : undefined;

      failures.push({
        id: typeof item === 'object' && item !== null && 'id' in item && typeof item.id === 'number'
          ? item.id
          : 'unknown',
        name: itemName,
        missingKeys,
      });
    }
  }

  // Write results to JSON file
  const results = {
    timestamp: new Date().toISOString(),
    totalItems: items.length,
    itemsWithMissingKeys: failures.length,
    failures: failures,
  };

  writeFileSync(outputPath, JSON.stringify(results, null, 2), 'utf-8');

  if (failures.length === 0) {
    console.log(`OK: ${items.length} items validated`);
    console.log(`Results written to: ${outputPath}`);
    return;
  }

  console.log(`Found ${failures.length} item(s) with missing keys`);
  console.log(`Results written to: ${outputPath}\n`);

  // Also print summary to console
  for (const failure of failures) {
    console.log(`ID: ${failure.id}${failure.name ? ` (${failure.name})` : ''}`);
    console.log(`Missing keys: ${failure.missingKeys.join(', ')}\n`);
  }
  process.exitCode = 1;
}

main();
