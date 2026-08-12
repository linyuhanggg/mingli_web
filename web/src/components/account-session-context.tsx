"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  getAccount,
  subscribeAccountSessionInvalidation,
  type AccountResponse,
  type LoginIdentitySummary,
} from "@/lib/api";


export type AccountSessionState =
  | { status: "checking" }
  | { status: "signedOut" }
  | { status: "error"; message: string }
  | { status: "signedIn"; account: AccountResponse };

type AccountSessionContextValue = {
  state: AccountSessionState;
  refresh: (options?: { force?: boolean }) => Promise<AccountSessionState>;
  markSignedOut: () => void;
};

const AccountSessionContext = createContext<AccountSessionContextValue | null>(null);

function readableError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "服务暂时不可用，请稍后重试。";
}

export function primaryLoginIdentity(
  account: AccountResponse,
): LoginIdentitySummary | null {
  return account.identities.find((identity) => identity.provider === "email")
    ?? account.identities[0]
    ?? null;
}

export function AccountSessionProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [state, setState] = useState<AccountSessionState>({ status: "checking" });
  const mountedRef = useRef(false);
  const requestGenerationRef = useRef(0);
  const inFlightRefreshRef = useRef<Promise<AccountSessionState> | null>(null);
  const invalidationRefreshRef = useRef<Promise<void> | null>(null);

  const refresh = useCallback((options?: { force?: boolean }): Promise<AccountSessionState> => {
    if (inFlightRefreshRef.current && !options?.force) {
      return inFlightRefreshRef.current;
    }

    const requestGeneration = requestGenerationRef.current + 1;
    requestGenerationRef.current = requestGeneration;
    const request = (async () => {
      let nextState: AccountSessionState;
      try {
        const account = await getAccount();
        nextState = { status: "signedIn", account };
      } catch (error) {
        nextState = error instanceof ApiError && error.status === 401
          ? { status: "signedOut" }
          : { status: "error", message: readableError(error) };
      }

      if (
        mountedRef.current
        && requestGenerationRef.current === requestGeneration
      ) {
        setState(nextState);
      }
      return nextState;
    })();

    inFlightRefreshRef.current = request;
    void request.finally(() => {
      if (inFlightRefreshRef.current === request) {
        inFlightRefreshRef.current = null;
      }
    });
    return request;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    function refreshVisibleSession() {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    }
    const unsubscribe = subscribeAccountSessionInvalidation(() => {
      if (invalidationRefreshRef.current) {
        return invalidationRefreshRef.current;
      }

      const invalidationRefresh = (async () => {
        const currentRefresh = inFlightRefreshRef.current;
        if (currentRefresh) {
          await currentRefresh;
        }
        if (!mountedRef.current) return;
        await refresh({ force: true });
      })();
      invalidationRefreshRef.current = invalidationRefresh;
      void invalidationRefresh.finally(() => {
        if (invalidationRefreshRef.current === invalidationRefresh) {
          invalidationRefreshRef.current = null;
        }
      });
      return invalidationRefresh;
    });
    window.addEventListener("focus", refreshVisibleSession);
    document.addEventListener("visibilitychange", refreshVisibleSession);
    void refresh();

    return () => {
      unsubscribe();
      window.removeEventListener("focus", refreshVisibleSession);
      document.removeEventListener("visibilitychange", refreshVisibleSession);
      mountedRef.current = false;
      requestGenerationRef.current += 1;
      inFlightRefreshRef.current = null;
      invalidationRefreshRef.current = null;
    };
  }, [refresh]);

  const markSignedOut = useCallback(() => {
    requestGenerationRef.current += 1;
    inFlightRefreshRef.current = null;
    setState({ status: "signedOut" });
  }, []);

  const value = useMemo(
    () => ({ state, refresh, markSignedOut }),
    [markSignedOut, refresh, state],
  );

  return (
    <AccountSessionContext.Provider value={value}>
      {children}
    </AccountSessionContext.Provider>
  );
}

/**
 * Reuses the nearest account session when one exists and creates a single
 * client-side probe only at the owning shell boundary otherwise.
 */
export function AccountSessionBoundary({ children }: Readonly<{ children: ReactNode }>) {
  const existing = useContext(AccountSessionContext);
  if (existing) {
    return children;
  }
  return <AccountSessionProvider>{children}</AccountSessionProvider>;
}

export function useAccountSession(): AccountSessionContextValue {
  const context = useContext(AccountSessionContext);
  if (!context) {
    throw new Error("useAccountSession must be used inside AccountSessionBoundary");
  }
  return context;
}

export function useOptionalAccountSession(): AccountSessionContextValue | null {
  return useContext(AccountSessionContext);
}
