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
  /** Whether document search can read this file: "indexed", "pending",
   * "empty" or "unreadable". Shown to the user, because a document nobody
   * can search is a gap in the record. */
  index_status: string;
  index_detail: string | null;
  /** Text inside the document written to instruct an AI. A finding about
   * the document, so it is surfaced on the document. */
  injection_findings: string[] | null;
}
