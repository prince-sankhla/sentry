export function formatMoney(value: string | null, currency: string): string {
  if (value === null) {
    return "Not disclosed";
  }

  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} ${currency}`;
  }

  return new Intl.NumberFormat("en", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0
  }).format(amount);
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  INR: "₹",
  USD: "$",
  EUR: "€",
  GBP: "£",
  UAH: "₴"
};

export function currencySymbol(currency: string): string {
  return CURRENCY_SYMBOLS[currency] ?? `${currency} `;
}

/** Compact figure for dashboards: ₹1.2Cr / $3.4M. Indian units for INR. */
export function formatCompactMoney(value: string | null, currency = "INR"): string {
  if (value === null || value === undefined) return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value}`;
  const sym = currencySymbol(currency);
  const abs = Math.abs(amount);
  if (currency === "INR") {
    if (abs >= 1e7) return `${sym}${(amount / 1e7).toFixed(2)}Cr`;
    if (abs >= 1e5) return `${sym}${(amount / 1e5).toFixed(2)}L`;
    if (abs >= 1e3) return `${sym}${(amount / 1e3).toFixed(1)}K`;
    return `${sym}${amount.toFixed(0)}`;
  }
  if (abs >= 1e9) return `${sym}${(amount / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sym}${(amount / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sym}${(amount / 1e3).toFixed(1)}K`;
  return `${sym}${amount.toFixed(0)}`;
}

export function formatMoneyFull(value: string | null, currency = "INR"): string {
  if (value === null) return "Not disclosed";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value} ${currency}`;
  return `${currencySymbol(currency)}${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0
  }).format(amount)}`;
}

export function formatNumber(value: number | string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return new Intl.NumberFormat("en-IN").format(n);
}

export function formatDate(value: string | null): string {
  if (!value) {
    return "No date";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(date);
}
