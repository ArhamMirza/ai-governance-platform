import { useRef, useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { evidenceApi } from "../api";
import {
  useCreateFolder,
  useDeleteEvidence,
  useDeleteFolder,
  useEvidenceList,
  useFolders,
  useUploadEvidence,
} from "../hooks";

interface DocumentBrowserProps {
  entityType: string;
  entityId: number;
}

interface PathEntry {
  id: number;
  name: string;
}

export function DocumentBrowser({ entityType, entityId }: DocumentBrowserProps) {
  const [path, setPath] = useState<PathEntry[]>([]);
  const [newFolderName, setNewFolderName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taggingEvidenceId, setTaggingEvidenceId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentFolderId = path.length > 0 ? path[path.length - 1].id : null;

  const { data: folders, isLoading: foldersLoading } = useFolders(
    entityType,
    entityId,
    currentFolderId,
  );
  const { data: documents, isLoading: documentsLoading } = useEvidenceList(
    entityType,
    entityId,
    currentFolderId,
  );
  const createFolder = useCreateFolder(entityType, entityId, currentFolderId);
  const deleteFolder = useDeleteFolder(entityType, entityId, currentFolderId);
  const uploadEvidence = useUploadEvidence(entityType, entityId, currentFolderId);
  const deleteEvidence = useDeleteEvidence(entityType, entityId, currentFolderId);

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    setError(null);
    try {
      await createFolder.mutateAsync(newFolderName.trim());
      setNewFolderName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create folder");
    }
  };

  const handleDeleteFolder = async (folderId: number) => {
    setError(null);
    try {
      await deleteFolder.mutateAsync(folderId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete folder");
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setError(null);
    try {
      await uploadEvidence.mutateAsync(files[0]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload document");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteEvidence = async (evidenceId: number) => {
    setError(null);
    try {
      await deleteEvidence.mutateAsync(evidenceId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete document");
    }
  };

  return (
    <div className="document-browser">
      <nav aria-label="breadcrumb">
        <button onClick={() => setPath([])} disabled={path.length === 0}>
          Root
        </button>
        {path.map((entry, index) => (
          <span key={entry.id}>
            {" / "}
            <button onClick={() => setPath(path.slice(0, index + 1))}>{entry.name}</button>
          </span>
        ))}
      </nav>

      {error && <p role="alert">{error}</p>}

      <div className="document-browser-toolbar">
        <input
          value={newFolderName}
          onChange={(e) => setNewFolderName(e.target.value)}
          placeholder="New folder name"
          aria-label="New folder name"
        />
        <button onClick={handleCreateFolder} disabled={createFolder.isPending}>
          New Folder
        </button>
      </div>

      <div className="document-browser-toolbar">
        <label htmlFor="document-upload">Upload document</label>
        <input
          id="document-upload"
          ref={fileInputRef}
          type="file"
          onChange={(e) => handleUpload(e.target.files)}
          disabled={uploadEvidence.isPending}
        />
      </div>

      {foldersLoading ? (
        <p>Loading folders...</p>
      ) : (
        <ul className="document-browser-list">
          {folders?.map((folder) => (
            <li key={folder.id}>
              <button
                className="document-browser-row-name"
                onClick={() => setPath([...path, { id: folder.id, name: folder.name }])}
              >
                📁 {folder.name}
              </button>
              <button onClick={() => handleDeleteFolder(folder.id)}>Delete</button>
            </li>
          ))}
        </ul>
      )}

      {documentsLoading ? (
        <p>Loading documents...</p>
      ) : documents && documents.length === 0 && (!folders || folders.length === 0) ? (
        <p>No documents yet.</p>
      ) : (
        <ul className="document-browser-list">
          {documents?.map((doc) => (
            <li key={doc.id}>
              <a
                className="document-browser-row-name"
                href={evidenceApi.downloadUrl(doc.id)}
                target="_blank"
                rel="noreferrer"
              >
                {doc.filename}
              </a>
              <button
                onClick={() =>
                  setTaggingEvidenceId(taggingEvidenceId === doc.id ? null : doc.id)
                }
              >
                {taggingEvidenceId === doc.id ? "Hide Tags" : "Tags"}
              </button>
              <button onClick={() => handleDeleteEvidence(doc.id)}>Delete</button>
              {taggingEvidenceId === doc.id && (
                <FrameworkTagPicker entityType="Evidence" entityId={doc.id} />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
