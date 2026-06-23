/**
 * Curated sample trips for the landing page "Explore Sample Trips" modal.
 * Each sample maps to a UserQuery that can be loaded into /plan.
 */

import type { UserQuery } from "./types";

export interface SampleTrip {
  id: string;
  name: string;
  route: string;
  days: number;
  budget: number;
  safety: number;
  weather: string;
  highlights: string[];
  badges: string[];
  query: UserQuery;
  imageQuery: string;
}

export const SAMPLE_TRIPS: SampleTrip[] = [
  {
    id: "hunza-explorer",
    name: "Hunza Explorer",
    route: "Islamabad → Naran → Hunza",
    days: 7,
    budget: 185000,
    safety: 91,
    weather: "Excellent",
    highlights: ["Baltit Fort", "Attabad Lake", "Babusar Pass"],
    badges: ["Family Friendly", "Photography Optimized", "Budget Fit"],
    imageQuery: "Hunza Valley Karimabad Pakistan autumn",
    query: {
      group_size: 4,
      group_composition: "family",
      budget_pkr: 185000,
      days: 7,
      travel_month: 7,
      travel_mode_pref: "road",
      origin_city: "islamabad",
      style_tags: ["scenic", "cultural", "photography"],
      difficulty_tolerance: 3,
      is_foreign_traveller: false,
      elderly_in_group: false,
      kids_in_group: false,
      altitude_sensitive: false,
      luxury_stays_needed: false,
      motion_sickness: false,
      road_trip_only: false,
    },
  },
  {
    id: "skardu-adventure",
    name: "Skardu Adventure",
    route: "Islamabad → Skardu → Deosai",
    days: 5,
    budget: 220000,
    safety: 85,
    weather: "Good",
    highlights: ["Shangrila Lake", "Deosai Plains", "Shigar Valley"],
    badges: ["Adventure Packed", "Photography Optimized"],
    imageQuery: "Skardu Deosai Plains Pakistan mountains",
    query: {
      group_size: 3,
      group_composition: "friends",
      budget_pkr: 220000,
      days: 5,
      travel_month: 8,
      travel_mode_pref: "air",
      origin_city: "islamabad",
      style_tags: ["adventure", "photography", "trekking"],
      difficulty_tolerance: 4,
      is_foreign_traveller: false,
      elderly_in_group: false,
      kids_in_group: false,
      altitude_sensitive: false,
      luxury_stays_needed: false,
      motion_sickness: false,
      road_trip_only: false,
    },
  },
  {
    id: "swat-escape",
    name: "Swat Valley Escape",
    route: "Islamabad → Swat → Kalam",
    days: 4,
    budget: 80000,
    safety: 94,
    weather: "Excellent",
    highlights: ["Kalam Valley", "Mahodand Lake", "Malam Jabba"],
    badges: ["Budget Fit", "Family Friendly", "Relaxation"],
    imageQuery: "Swat Kalam Valley Pakistan green mountains",
    query: {
      group_size: 5,
      group_composition: "family",
      budget_pkr: 80000,
      days: 4,
      travel_month: 6,
      travel_mode_pref: "road",
      origin_city: "islamabad",
      style_tags: ["relaxing", "scenic", "food"],
      difficulty_tolerance: 2,
      is_foreign_traveller: false,
      elderly_in_group: true,
      kids_in_group: true,
      altitude_sensitive: false,
      luxury_stays_needed: false,
      motion_sickness: false,
      road_trip_only: false,
    },
  },
  {
    id: "fairy-meadows-trek",
    name: "Fairy Meadows Trek",
    route: "Islamabad → Raikot → Fairy Meadows",
    days: 6,
    budget: 150000,
    safety: 78,
    weather: "Good",
    highlights: ["Nanga Parbat Base", "Fairy Meadows Camp", "Bunar Village"],
    badges: ["Adventure Packed", "Photography Optimized"],
    imageQuery: "Fairy Meadows Nanga Parbat Pakistan meadow",
    query: {
      group_size: 2,
      group_composition: "couple",
      budget_pkr: 150000,
      days: 6,
      travel_month: 7,
      travel_mode_pref: "road",
      origin_city: "islamabad",
      style_tags: ["adventure", "trekking", "photography"],
      difficulty_tolerance: 4,
      is_foreign_traveller: false,
      elderly_in_group: false,
      kids_in_group: false,
      altitude_sensitive: false,
      luxury_stays_needed: false,
      motion_sickness: false,
      road_trip_only: true,
    },
  },
];
