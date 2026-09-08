"use client";

import { useEffect } from "react";

const TARGETS: Record<string, string> = {
  "delhi-cwg": "FIELD-AUDIT-DELHI-CWG",
  "dhanbad-led": "FIELD-AUDIT-DHANBAD-LED",
};

export function AuditFieldBootstrap() {
  useEffect(() => {
    const key = new URLSearchParams(window.location.search).get("case");
    const target = key ? TARGETS[key] : null;
    if (!target) return;

    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const select = document.querySelector<HTMLSelectElement>("main select");
      if (!select) {
        if (attempts > 40) window.clearInterval(timer);
        return;
      }
      const option = Array.from(select.options).find((item) => item.value === target);
      if (!option) {
        if (attempts > 40) window.clearInterval(timer);
        return;
      }

      const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
      setter?.call(select, target);
      select.dispatchEvent(new Event("change", { bubbles: true }));
      window.clearInterval(timer);
    }, 150);

    return () => window.clearInterval(timer);
  }, []);

  return null;
}
