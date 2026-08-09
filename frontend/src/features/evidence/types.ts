export interface Folder {
  id: number;
  entity_type: string;
  entity_id: number;
  parent_folder_id: number | null;
  name: string;
  created_at: string;
}

export interface Evidence {
  id: number;
  entity_type: string;
  entity_id: number;
  folder_id: number | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  description: string | null;
  uploaded_by: number | null;
  uploaded_at: string;
}
