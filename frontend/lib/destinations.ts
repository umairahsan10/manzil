// Destination metadata shared across the frontend.
// Maps backend destination IDs to human-readable names and coordinates.

export interface DestinationMeta {
  id: string;
  name: string;
  shortName: string;
  region: string;
  coords: [number, number];
  imageQuery: string;
}

export const DESTINATIONS: Record<string, DestinationMeta> = {
  "hunza-karimabad": {
    id: "hunza-karimabad",
    name: "Karimabad, Hunza",
    shortName: "Hunza",
    region: "Gilgit-Baltistan",
    coords: [74.65, 36.3167],
    imageQuery: "Karimabad Hunza Valley Pakistan",
  },
  skardu: {
    id: "skardu",
    name: "Skardu",
    shortName: "Skardu",
    region: "Gilgit-Baltistan",
    coords: [75.6333, 35.2971],
    imageQuery: "Skardu Pakistan landscape",
  },
  naran: {
    id: "naran",
    name: "Naran",
    shortName: "Naran",
    region: "Khyber Pakhtunkhwa",
    coords: [73.6517, 34.9056],
    imageQuery: "Naran Kaghan Valley Pakistan",
  },
  "fairy-meadows": {
    id: "fairy-meadows",
    name: "Fairy Meadows",
    shortName: "Fairy Meadows",
    region: "Gilgit-Baltistan",
    coords: [74.5833, 35.3833],
    imageQuery: "Fairy Meadows Nanga Parbat Pakistan",
  },
  murree: {
    id: "murree",
    name: "Murree",
    shortName: "Murree",
    region: "Punjab",
    coords: [73.3833, 33.9067],
    imageQuery: "Murree Pakistan hills",
  },
  gilgit: {
    id: "gilgit",
    name: "Gilgit",
    shortName: "Gilgit",
    region: "Gilgit-Baltistan",
    coords: [74.3087, 35.9221],
    imageQuery: "Gilgit Pakistan mountains",
  },
  passu: {
    id: "passu",
    name: "Passu",
    shortName: "Passu",
    region: "Gilgit-Baltistan",
    coords: [74.8667, 36.4717],
    imageQuery: "Passu Cathedral Peaks Pakistan",
  },
  attabad: {
    id: "attabad",
    name: "Attabad Lake",
    shortName: "Attabad",
    region: "Gilgit-Baltistan",
    coords: [74.8606, 36.3344],
    imageQuery: "Attabad Lake Hunza Pakistan",
  },
  khaplu: {
    id: "khaplu",
    name: "Khaplu",
    shortName: "Khaplu",
    region: "Gilgit-Baltistan",
    coords: [76.3667, 35.15],
    imageQuery: "Khaplu Palace Pakistan",
  },
  "swat-kalam": {
    id: "swat-kalam",
    name: "Kalam, Swat",
    shortName: "Swat",
    region: "Khyber Pakhtunkhwa",
    coords: [72.5783, 35.4836],
    imageQuery: "Kalam Swat Valley Pakistan",
  },
  shogran: {
    id: "shogran",
    name: "Shogran",
    shortName: "Shogran",
    region: "Khyber Pakhtunkhwa",
    coords: [73.45, 34.65],
    imageQuery: "Shogran Siri Paye Pakistan",
  },
  neelum: {
    id: "neelum",
    name: "Neelum Valley",
    shortName: "Neelum",
    region: "Azad Kashmir",
    coords: [73.9, 34.55],
    imageQuery: "Neelum Valley Kashmir Pakistan",
  },
  deosai: {
    id: "deosai",
    name: "Deosai Plains",
    shortName: "Deosai",
    region: "Gilgit-Baltistan",
    coords: [75.4, 34.9667],
    imageQuery: "Deosai Plains Pakistan",
  },
  chitral: {
    id: "chitral",
    name: "Chitral",
    shortName: "Chitral",
    region: "Khyber Pakhtunkhwa",
    coords: [71.7833, 35.85],
    imageQuery: "Chitral Pakistan mountains",
  },
  khunjerab: {
    id: "khunjerab",
    name: "Khunjerab Pass",
    shortName: "Khunjerab",
    region: "Gilgit-Baltistan",
    coords: [75.42, 36.85],
    imageQuery: "Khunjerab Pass Karakoram Highway Pakistan",
  },
};

export function getDestination(id: string): DestinationMeta | undefined {
  return DESTINATIONS[id];
}

export function getDestinationName(id: string): string {
  return DESTINATIONS[id]?.name || id;
}

export function getDestinationShortName(id: string): string {
  return DESTINATIONS[id]?.shortName || id;
}

export function getDestinationImageQuery(id: string): string {
  return DESTINATIONS[id]?.imageQuery || `${id} Pakistan`;
}

export function getRouteStops(ids: string[]) {
  return ids
    .map((id, idx) => {
      const dest = getDestination(id);
      if (!dest) return null;
      return {
        id: dest.id,
        name: dest.name,
        coords: dest.coords,
        index: idx + 1,
      };
    })
    .filter(Boolean) as {
    id: string;
    name: string;
    coords: [number, number];
    index: number;
  }[];
}

// --- Derived helpers for the results + trip detail pages ---

/**
 * Derive a fatigue score from total drive hours and days.
 * Returns "Low" | "Moderate" | "High"
 */
export function deriveFatigue(
  totalDriveHours: number | undefined,
  days: number
): string {
  if (!totalDriveHours || days === 0) return "Low";
  const hoursPerDay = totalDriveHours / days;
  if (hoursPerDay > 7) return "High";
  if (hoursPerDay > 4) return "Moderate";
  return "Low";
}

/**
 * Derive badges for a trip card from the candidate + query.
 */
export function deriveBadges(
  candidate: {
    estimated_cost?: number;
    total_cost_pkr?: number;
    destinations?: string[];
    days?: number;
  },
  query: {
    group_composition: string;
    budget_pkr: number;
    style_tags: string[];
  }
): string[] {
  const badges: string[] = [];
  const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;

  if (query.group_composition === "family") badges.push("Family Friendly");
  if (query.style_tags.includes("photography")) badges.push("Photography Optimized");
  if (cost > 0 && cost <= query.budget_pkr) badges.push("Budget Fit");
  if (query.style_tags.includes("adventure")) badges.push("Adventure Packed");
  if (query.style_tags.includes("luxury")) badges.push("Premium Stays");
  if (query.style_tags.includes("relaxing")) badges.push("Relaxation");

  return badges.slice(0, 3);
}

/**
 * Generate a catchy trip name from route destinations.
 */
export function deriveTripName(candidate: {
  label?: string;
  destinations?: string[];
}): string {
  if (candidate.label && candidate.label.length < 40) return candidate.label;
  const dests = candidate.destinations || [];
  if (dests.length === 0) return "Custom Trip";
  const first = getDestinationShortName(dests[0]);
  const last = getDestinationShortName(dests[dests.length - 1]);
  if (dests.length === 1) return `${first} Getaway`;
  if (dests.length === 2) return `${first} → ${last} Journey`;
  return `${first} Explorer`;
}
