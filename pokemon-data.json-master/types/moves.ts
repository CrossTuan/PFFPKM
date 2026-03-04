export interface MoveName {
  english: string;
  japanese: string;
  french: string;
  chinese: string;
}

export interface Move {
  id: string;
  name: MoveName;
  type: string;
  category: 'Physical' | 'Special' | 'Status' | '???';
  pp: string;
  power: string;
  accuracy: string;
}
