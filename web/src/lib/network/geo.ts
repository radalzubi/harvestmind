/**
 * Geography the twin knows without being told: the lanes ZAAD already
 * tags suppliers with (aqaba, red_sea, suez, hormuz, road_saudi), the ports
 * and chokepoints they pass, and country centroids for facilities whose
 * exact position the operator has not given. Coordinates are [lon, lat].
 */

export type LonLat = [number, number];

export const PORTS: Record<string, { name: string; at: LonLat; country: string }> = {
  aqaba: { name: "Port of Aqaba", at: [35.0, 29.52], country: "JO" },
  jeddah: { name: "Jeddah Islamic Port", at: [39.15, 21.47], country: "SA" },
  jebel_ali: { name: "Jebel Ali", at: [55.06, 25.01], country: "AE" },
  dammam: { name: "King Abdulaziz Port, Dammam", at: [50.2, 26.45], country: "SA" },
  port_said: { name: "Port Said", at: [32.3, 31.26], country: "EG" },
  alexandria: { name: "Alexandria", at: [29.92, 31.2], country: "EG" },
  mersin: { name: "Mersin", at: [34.63, 36.79], country: "TR" },
  izmir: { name: "Izmir (Alsancak)", at: [27.14, 38.44], country: "TR" },
  yantian: { name: "Shenzhen (Yantian)", at: [114.27, 22.57], country: "CN" },
  shanghai: { name: "Shanghai (Yangshan)", at: [122.06, 30.63], country: "CN" },
  singapore: { name: "Singapore", at: [103.75, 1.26], country: "SG" },
  mundra: { name: "Mundra", at: [69.7, 22.74], country: "IN" },
  rotterdam: { name: "Rotterdam", at: [4.13, 51.95], country: "NL" },
  haifa: { name: "Haifa", at: [35.0, 32.82], country: "IL" },
};

export const CHOKEPOINTS: Record<string, { name: string; at: LonLat }> = {
  suez: { name: "Suez Canal", at: [32.55, 30.0] },
  bab_el_mandeb: { name: "Bab el-Mandeb Strait", at: [43.35, 12.6] },
  hormuz: { name: "Strait of Hormuz", at: [56.3, 26.55] },
  malacca: { name: "Strait of Malacca", at: [100.6, 3.2] },
};

/** Waypoints sea lanes follow between well-known points, so a lane between any two ports can be assembled. */
const SEA: Record<string, LonLat[]> = {
  // Gulf of Aqaba up from the Red Sea
  red_sea_to_aqaba: [[40.0, 18.0], [37.6, 22.5], [36.2, 25.5], [34.55, 27.9], [34.65, 28.6], [34.85, 29.3], [35.0, 29.52]],
  // Mediterranean into the Red Sea through Suez
  med_to_red_sea: [[32.3, 31.26], [32.55, 30.0], [32.6, 29.7], [33.3, 28.3], [34.3, 27.6]],
  // Indian Ocean approach to the Red Sea
  aden_to_red_sea: [[48.0, 12.4], [43.35, 12.6], [42.2, 14.5], [40.0, 18.0]],
  // East Asia to the Arabian Sea
  asia_to_arabian: [[114.27, 22.57], [112.0, 16.0], [108.5, 8.0], [104.5, 2.0], [103.75, 1.26], [100.6, 3.2], [95.0, 6.0], [80.0, 5.5], [65.0, 10.0], [58.0, 13.0]],
  arabian_to_hormuz: [[58.0, 13.0], [59.0, 22.0], [57.2, 24.6], [56.3, 26.55], [55.06, 25.01]],
};

/** Lane tag -> how ZAAD describes it, which chokepoints it crosses and which port it lands at. */
export const LANE_CATALOG: Record<string, { name: string; kind: "ocean" | "road"; chokepoints: string[]; port: string | null; path: LonLat[] }> = {
  red_sea: { name: "Red Sea route", kind: "ocean", chokepoints: ["bab_el_mandeb"], port: "aqaba",
             path: [...SEA.aden_to_red_sea, ...SEA.red_sea_to_aqaba.slice(1)] },
  aqaba: { name: "Aqaba (sea)", kind: "ocean", chokepoints: ["bab_el_mandeb", "suez"], port: "aqaba",
           path: [...SEA.aden_to_red_sea, ...SEA.red_sea_to_aqaba.slice(1)] },
  sea: { name: "Sea route to Aqaba", kind: "ocean", chokepoints: ["bab_el_mandeb"], port: "aqaba",
         path: [...SEA.aden_to_red_sea, ...SEA.red_sea_to_aqaba.slice(1)] },
  suez: { name: "Suez route", kind: "ocean", chokepoints: ["suez"], port: "aqaba",
          path: [[25.5, 36.0], [30.5, 33.0], ...SEA.med_to_red_sea, ...SEA.red_sea_to_aqaba.slice(3)] },
  hormuz: { name: "Strait of Hormuz route", kind: "ocean", chokepoints: ["hormuz"], port: "jebel_ali",
            path: SEA.arabian_to_hormuz },
  gulf: { name: "Gulf route", kind: "ocean", chokepoints: ["hormuz"], port: "jebel_ali", path: SEA.arabian_to_hormuz },
  road_saudi: { name: "Road lane through Saudi Arabia", kind: "road", chokepoints: [], port: null,
                path: [[55.06, 25.01], [51.5, 25.3], [46.7, 24.7], [43.0, 27.0], [39.9, 30.0], [37.5, 31.2], [35.93, 31.95]] },
};

/** Country centroids for facilities placed by region only. */
export const REGION_AT: Record<string, LonLat> = {
  JO: [36.2, 31.3], SA: [45.0, 24.0], AE: [54.3, 24.0], EG: [30.8, 26.8], KW: [47.6, 29.3], QA: [51.2, 25.3],
  BH: [50.55, 26.05], OM: [56.0, 21.0], IQ: [43.7, 33.2], LB: [35.85, 33.85], SY: [38.0, 35.0], TR: [35.2, 39.0],
  IL: [34.9, 31.5], PS: [35.2, 31.9], IN: [78.9, 20.6], CN: [104.2, 35.9], DE: [10.4, 51.2], NL: [5.3, 52.1],
  GB: [-1.5, 52.5], US: [-98.5, 39.8], FR: [2.2, 46.2], IT: [12.6, 42.5], ES: [-3.7, 40.4], PK: [69.3, 30.4],
};

export function haversineKm(a: LonLat, b: LonLat): number {
  const R = 6371, d = Math.PI / 180;
  const dLat = (b[1] - a[1]) * d, dLon = (b[0] - a[0]) * d;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * d) * Math.cos(b[1] * d) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function pathLengthKm(path: LonLat[]): number {
  let s = 0;
  for (let i = 1; i < path.length; i++) s += haversineKm(path[i - 1], path[i]);
  return s;
}

/** Point at fraction t (0..1) of the way along a polyline, by distance. */
export function pointAlong(path: LonLat[], t: number): LonLat {
  if (path.length === 0) return [0, 0];
  if (path.length === 1) return path[0];
  const total = pathLengthKm(path);
  let target = Math.max(0, Math.min(1, t)) * total;
  for (let i = 1; i < path.length; i++) {
    const seg = haversineKm(path[i - 1], path[i]);
    if (target <= seg || i === path.length - 1) {
      const f = seg === 0 ? 0 : Math.max(0, Math.min(1, target / seg));
      return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f];
    }
    target -= seg;
  }
  return path[path.length - 1];
}

export function bounds(points: LonLat[]): [LonLat, LonLat] | null {
  if (points.length === 0) return null;
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  for (const [lon, lat] of points) {
    minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
  }
  return [[minLon, minLat], [maxLon, maxLat]];
}
