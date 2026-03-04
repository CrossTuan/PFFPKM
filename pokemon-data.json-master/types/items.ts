export interface ItemName {
  english: string;
  japanese: string;
  chinese: string;
}

export interface Item {
  id: number;
  name: ItemName;
  type: string;
  description: string;
}
