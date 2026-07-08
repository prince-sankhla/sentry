/**
 * India state canonicalization + centroids.
 *
 * The backend geography endpoint returns free-form region strings inferred from
 * buyer names; we map them onto canonical state names that match the TopoJSON
 * `st_nm` property, and provide [lng, lat] centroids for animated hotspot markers.
 */

const ALIASES: Record<string, string> = {
  "orissa": "Odisha",
  "odisha": "Odisha",
  "pondicherry": "Puducherry",
  "puducherry": "Puducherry",
  "uttaranchal": "Uttarakhand",
  "uttarakhand": "Uttarakhand",
  "nct of delhi": "Delhi",
  "delhi": "Delhi",
  "jammu & kashmir": "Jammu and Kashmir",
  "jammu and kashmir": "Jammu and Kashmir",
  "andaman & nicobar": "Andaman and Nicobar",
  "andaman and nicobar islands": "Andaman and Nicobar",
  "dadra & nagar haveli": "Dadra and Nagar Haveli",
  "daman & diu": "Daman and Diu",
  "telangana": "Telangana",
  "tamilnadu": "Tamil Nadu",
  "tamil nadu": "Tamil Nadu"
};

const CANONICAL = new Set([
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
  "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
  "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
  "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry",
  "Jammu and Kashmir", "Ladakh", "Chandigarh", "Andaman and Nicobar",
  "Dadra and Nagar Haveli", "Daman and Diu", "Lakshadweep"
]);

export function canonicalState(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (CANONICAL.has(trimmed)) return trimmed;
  const lower = trimmed.toLowerCase();
  if (ALIASES[lower]) return ALIASES[lower];
  // title-case match
  const title = trimmed.replace(/\b\w/g, (c) => c.toUpperCase());
  if (CANONICAL.has(title)) return title;
  return null;
}

/** [longitude, latitude] centroids for marker placement. */
export const STATE_CENTROIDS: Record<string, [number, number]> = {
  "Andhra Pradesh": [79.74, 15.9],
  "Arunachal Pradesh": [94.0, 28.2],
  "Assam": [92.9, 26.2],
  "Bihar": [85.3, 25.6],
  "Chhattisgarh": [81.8, 21.3],
  "Delhi": [77.1, 28.7],
  "Goa": [74.1, 15.4],
  "Gujarat": [71.6, 22.6],
  "Haryana": [76.1, 29.2],
  "Himachal Pradesh": [77.2, 31.9],
  "Jharkhand": [85.3, 23.6],
  "Karnataka": [75.7, 15.3],
  "Kerala": [76.3, 10.5],
  "Madhya Pradesh": [78.7, 23.5],
  "Maharashtra": [75.7, 19.7],
  "Manipur": [93.9, 24.7],
  "Meghalaya": [91.4, 25.5],
  "Mizoram": [92.9, 23.2],
  "Nagaland": [94.5, 26.1],
  "Odisha": [85.1, 20.9],
  "Punjab": [75.3, 31.1],
  "Rajasthan": [74.2, 27.0],
  "Sikkim": [88.5, 27.5],
  "Tamil Nadu": [78.3, 11.1],
  "Telangana": [79.0, 17.9],
  "Tripura": [91.7, 23.8],
  "Uttar Pradesh": [80.9, 26.8],
  "Uttarakhand": [79.3, 30.1],
  "West Bengal": [87.9, 23.5],
  "Puducherry": [79.8, 11.9],
  "Jammu and Kashmir": [75.3, 33.8],
  "Ladakh": [77.6, 34.2],
  "Chandigarh": [76.8, 30.7]
};
