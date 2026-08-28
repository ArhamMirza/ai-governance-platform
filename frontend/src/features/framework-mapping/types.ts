export interface TaggedItem {
  entity_type: string;
  entity_id: number;
  label: string;
}

export interface FrameworkMappingEntry {
  id: number;
  framework: string;
  code: string;
  title: string;
  description: string | null;
  category: string;
  tagged_items: TaggedItem[];
}
