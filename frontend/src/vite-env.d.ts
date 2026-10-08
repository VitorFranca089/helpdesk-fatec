/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Endereço do backend, sem o /api no fim. Ex.: http://localhost:8000 */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
