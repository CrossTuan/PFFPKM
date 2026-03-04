import { readFileSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';
import type { Pokemon } from '../types/pokedex.ts';

const repoRoot = resolve(import.meta.dir, '..');
const pokedexPath = join(repoRoot, 'pokedex.json');
const outputPath = join(repoRoot, 'scripts/pokedex-validation.json');

const REQUIRED_POKEMON_KEYS = ['id', 'name', 'type', 'base', 'species', 'description', 'evolution', 'profile'] as const;
const REQUIRED_NAME_KEYS = ['english', 'japanese', 'chinese', 'french'] as const;
const REQUIRED_BASE_KEYS = ['HP', 'Attack', 'Defense', 'Sp. Attack', 'Sp. Defense', 'Speed'] as const;
const REQUIRED_PROFILE_KEYS = ['height', 'weight', 'egg', 'ability', 'gender'] as const;

function readJson<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, 'utf-8'));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string');
}

function validatePokemon(pokemon: unknown): string[] {
  const missingKeys: string[] = [];

  if (typeof pokemon !== 'object' || pokemon === null) {
    return REQUIRED_POKEMON_KEYS.map(k => k);
  }

  const p = pokemon as Record<string, unknown>;

  // Check top-level required keys
  for (const key of REQUIRED_POKEMON_KEYS) {
    if (!(key in p)) {
      missingKeys.push(key);
    }
  }

  // Check id
  if (!('id' in p) || !isNumber(p.id)) {
    if (!missingKeys.includes('id')) {
      missingKeys.push('id');
    }
  }

  // Check name object and its required keys
  if (!('name' in p) || !p.name || typeof p.name !== 'object' || p.name === null) {
    if (!missingKeys.includes('name')) {
      missingKeys.push('name');
    }
  } else {
    const name = p.name as Record<string, unknown>;
    for (const key of REQUIRED_NAME_KEYS) {
      if (!(key in name) || !isNonEmptyString(name[key])) {
        missingKeys.push(`name.${key}`);
      }
    }
  }

  // Check type
  if (!('type' in p) || !isStringArray(p.type) || p.type.length === 0) {
    if (!missingKeys.includes('type')) {
      missingKeys.push('type');
    }
  }

  // Check base stats
  if (!('base' in p) || !p.base || typeof p.base !== 'object' || p.base === null) {
    if (!missingKeys.includes('base')) {
      missingKeys.push('base');
    }
  } else {
    const base = p.base as Record<string, unknown>;
    for (const key of REQUIRED_BASE_KEYS) {
      if (!(key in base) || !isNumber(base[key])) {
        missingKeys.push(`base.${key}`);
      }
    }
  }

  // Check species
  if (!('species' in p) || !isNonEmptyString(p.species)) {
    if (!missingKeys.includes('species')) {
      missingKeys.push('species');
    }
  }

  // Check description
  if (!('description' in p) || !isNonEmptyString(p.description)) {
    if (!missingKeys.includes('description')) {
      missingKeys.push('description');
    }
  }

  // Check evolution (must exist, but prev/next are optional)
  if (!('evolution' in p) || !p.evolution || typeof p.evolution !== 'object' || p.evolution === null) {
    if (!missingKeys.includes('evolution')) {
      missingKeys.push('evolution');
    }
  }

  // Check profile
  if (!('profile' in p) || !p.profile || typeof p.profile !== 'object' || p.profile === null) {
    if (!missingKeys.includes('profile')) {
      missingKeys.push('profile');
    }
  } else {
    const profile = p.profile as Record<string, unknown>;
    for (const key of REQUIRED_PROFILE_KEYS) {
      if (!(key in profile)) {
        missingKeys.push(`profile.${key}`);
      }
    }

    // Check profile.height
    if (!('height' in profile) || !isNonEmptyString(profile.height)) {
      if (!missingKeys.includes('profile.height')) {
        missingKeys.push('profile.height');
      }
    }

    // Check profile.weight
    if (!('weight' in profile) || !isNonEmptyString(profile.weight)) {
      if (!missingKeys.includes('profile.weight')) {
        missingKeys.push('profile.weight');
      }
    }

    // Check profile.egg
    if (!('egg' in profile) || !isStringArray(profile.egg)) {
      if (!missingKeys.includes('profile.egg')) {
        missingKeys.push('profile.egg');
      }
    }

    // Check profile.ability
    if (!('ability' in profile) || !Array.isArray(profile.ability)) {
      if (!missingKeys.includes('profile.ability')) {
        missingKeys.push('profile.ability');
      }
    }

    // Check profile.gender
    if (!('gender' in profile) || !isNonEmptyString(profile.gender)) {
      if (!missingKeys.includes('profile.gender')) {
        missingKeys.push('profile.gender');
      }
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
  const pokedex = readJson<Pokemon[]>(pokedexPath);

  const failures: Failure[] = [];

  for (const pokemon of pokedex) {
    const missingKeys = validatePokemon(pokemon);
    if (missingKeys.length > 0) {
      const pokemonName = typeof pokemon === 'object' && pokemon !== null && 'name' in pokemon &&
        typeof pokemon.name === 'object' && pokemon.name !== null && 'english' in pokemon.name &&
        typeof pokemon.name.english === 'string' ? pokemon.name.english : undefined;

      failures.push({
        id: typeof pokemon === 'object' && pokemon !== null && 'id' in pokemon && typeof pokemon.id === 'number'
          ? pokemon.id
          : 'unknown',
        name: pokemonName,
        missingKeys,
      });
    }
  }

  // Write results to JSON file
  const results = {
    timestamp: new Date().toISOString(),
    totalPokemon: pokedex.length,
    pokemonWithMissingKeys: failures.length,
    failures: failures,
  };

  writeFileSync(outputPath, JSON.stringify(results, null, 2), 'utf-8');

  if (failures.length === 0) {
    console.log(`OK: ${pokedex.length} Pokémon validated`);
    console.log(`Results written to: ${outputPath}`);
    return;
  }

  console.log(`Found ${failures.length} Pokémon with missing keys`);
  console.log(`Results written to: ${outputPath}\n`);

  // Also print summary to console
  for (const failure of failures) {
    console.log(`ID: ${failure.id}${failure.name ? ` (${failure.name})` : ''}`);
    console.log(`Missing keys: ${failure.missingKeys.join(', ')}\n`);
  }
  process.exitCode = 1;
}

main();
