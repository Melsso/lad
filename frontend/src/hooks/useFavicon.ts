import { useEffect, useRef } from "react";

const DEFAULT_ICON = "/favicon.svg";
const PROCESSING_ICON = "/favicon-processing.svg";
const READY_ICON = "/favicon-ready.svg";

export function useFavicon(isStreaming: boolean) {
  const wasStreamingRef = useRef(false);

  useEffect(() => {
    const setFavicon = (href: string) => {
      let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
      if (!link) {
        link = document.createElement("link");
        link.rel = "icon";
        document.head.appendChild(link);
      }
      link.href = href;
    };

    const handleVisibilityChange = () => {
      if (!document.hidden && !isStreaming) {
        wasStreamingRef.current = false;
        setFavicon(DEFAULT_ICON);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    if (isStreaming) {
      wasStreamingRef.current = true;
      setFavicon(PROCESSING_ICON);
    } else if (wasStreamingRef.current && document.hidden) {
      setFavicon(READY_ICON);
    } else if (!document.hidden) {
      wasStreamingRef.current = false;
      setFavicon(DEFAULT_ICON);
    }

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isStreaming]);
}
