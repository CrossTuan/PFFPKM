export interface PokemonName {
  english: string;
  japanese: string;
  chinese: string;
  french: string;
}

export interface BaseStats {
  HP: number;
  Attack: number;
  Defense: number;
  'Sp. Attack': number;
  'Sp. Defense': number;
  Speed: number;
}

export interface Evolution {
  prev?: [string, string];
  next?: Array<[string, string]>;
}

export interface Profile {
  height: string;
  weight: string;
  egg: string[];
  ability: Array<[string, string]>;
  gender: string;
}

export interface Pokemon {
  id: number;
  name: PokemonName;
  type: string[];
  base: BaseStats;
  species: string;
  description: string;
  evolution: Evolution;
  profile: Profile;
}
