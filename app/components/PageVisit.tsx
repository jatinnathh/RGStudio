"use client";

import { useEffect, useRef } from "react";

export function PageVisit() {
  const hasVisited = useRef(false);

  useEffect(() => {
    if (hasVisited.current) return;
    hasVisited.current = true;

    fetch("/api/notify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        event: "RGStudio Page Visit",
        details: `A visitor accessed the RGStudio site.`,
      }),
    }).catch(console.error);
  }, []);

  return null;
}
