"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "sentry-theme";

type Theme = "dark" | "light";

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("sentry-light", theme === "light");
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

function announceTheme(theme: Theme) {
  window.dispatchEvent(new CustomEvent("sentry:theme-change", { detail: theme }));
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const next: Theme = stored === "light" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    announceTheme(next);
  }, []);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
    announceTheme(next);
  }

  const isLight = theme === "light";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      title={isLight ? "Dark mode" : "Light mode"}
      className="fixed bottom-5 right-5 z-[100] grid h-11 w-11 place-items-center rounded-full border border-border bg-surface text-muted shadow-lg transition-all duration-200 hover:border-border-strong hover:bg-surface-2 hover:text-accent"
    >
      {isLight ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
    </button>
  );
}
