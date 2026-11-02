import { useCallback, useEffect, useRef, useState } from "react";

// Pide datos al montar la pantalla. Si la pantalla se cierra o se vuelve a pedir antes de que
// llegue la respuesta, la respuesta vieja se descarta.
export function useRequest(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const ticket = useRef(0);

  const run = useCallback(() => {
    const mine = ++ticket.current;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    fetcher()
      .then((data) => mine === ticket.current && setState({ data, error: null, loading: false }))
      .catch((error) => mine === ticket.current && setState({ data: null, error, loading: false }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
    return () => {
      ticket.current += 1;
    };
  }, [run]);

  return { ...state, reload: run };
}
