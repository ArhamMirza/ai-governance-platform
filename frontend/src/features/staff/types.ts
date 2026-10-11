export interface StaffDocument {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
}

/** An approved policy or procedure shared with employees -- nothing more of
 * the record than this. */
export interface StaffLibraryItem {
  kind: "policy" | "procedure";
  id: number;
  title: string;
  description: string | null;
  version: number;
  effective_date: string | null;
  documents: StaffDocument[];
}
