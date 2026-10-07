export interface AIRole {
  code: string;
  label: string;
  /** The main role this sub-role belongs to, e.g. "AI producer". */
  parent: string;
  description: string;
}
