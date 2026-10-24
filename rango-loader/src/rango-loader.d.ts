export type RangoLoaderMode = 'initial' | 'auth' | 'page' | 'local';
export type RangoTheme = 'auto' | 'light' | 'dark' | (() => 'light' | 'dark');

export interface RangoLoaderOptions {
  mode?: RangoLoaderMode;
  /** Onde montar (padrão: document.body). */
  container?: HTMLElement | null;
  /** Obrigatório no modo 'local'. */
  target?: HTMLElement | null;
  /** Integre ao seu provedor de tema; 'auto' lê data-theme / classe "dark" / prefers-color-scheme. */
  theme?: RangoTheme;
  /** ms antes de exibir (evita piscar). Padrão: initial/auth 0, page 120, local 200. */
  appearAfter?: number;
  reduceMotion?: 'auto' | boolean;
  zIndex?: number;
  labels?: { status?: string; tagline?: string };
}

export interface RangoLoader {
  readonly mode: RangoLoaderMode;
  readonly state: 'idle' | 'showing' | 'exiting';
  readonly isVisible: boolean;
  readonly element: HTMLElement | null;
  start(): RangoLoader;
  hide(detail?: unknown): RangoLoader;
  fail(error?: unknown): RangoLoader;
  cancel(reason?: unknown): RangoLoader;
  destroy(): void;
  whenReady<T extends readonly unknown[]>(promises: T | Promise<unknown>, opts?: { signal?: AbortSignal }): Promise<unknown>;
  track<T>(promise: Promise<T>, opts?: { signal?: AbortSignal }): Promise<T>;
  on(event: 'show' | 'ready' | 'error' | 'cancel' | 'hidden', fn: (e: CustomEvent) => void): () => void;
}

export function createRangoLoader(options?: RangoLoaderOptions): RangoLoader;
export const CHANNEL_IDS: string[];
