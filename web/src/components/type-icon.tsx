import type { ReactElement } from "react";

/** Curated monochrome icon registry — every user type picks from these.
 * Names are Material Symbols identifiers (snake_case ligatures); unknown
 * names fall back to `inventory_2`. The font ships every glyph, so the
 * registry is a plain name list — the picker filters it client-side. */
export const ICON_NAMES: string[] = [
  "alarm", "anchor", "archive", "arrow_forward", "alternate_email",
  "backpack", "badge", "payments", "bar_chart", "battery_full", "science",
  "bed", "sports_bar", "notifications", "directions_bike", "currency_bitcoin",
  "bluetooth", "sailing", "pets", "book", "bookmark", "smart_toy",
  "inventory_2", "neurology", "work", "brush", "bug_report", "apartment",
  "directions_bus", "cake", "calculate", "calendar_month", "calendar_clock",
  "calendar_today", "photo_camera", "directions_car", "smoking_rooms",
  "schedule", "cloud", "code", "local_cafe", "savings", "explore", "memory",
  "credit_card", "crown", "local_drink", "database", "diamond", "casino",
  "music_note", "egg", "description", "movie", "flag",
  "local_fire_department", "experiment", "folder", "podiatry",
  "sports_esports", "redeem", "water_drop", "eyeglasses", "public", "piano",
  "handyman", "tag", "headphones", "favorite", "home", "icecream", "image",
  "key", "laptop", "eco", "local_library", "lightbulb", "link", "lock",
  "attractions", "map", "location_on", "mic", "dark_mode", "landscape",
  "palette", "edit", "percent", "call", "pill", "local_pizza", "flight",
  "power", "extension", "rocket_launch", "straighten", "scale", "cut", "search",
  "shield", "shopping_bag", "shopping_cart", "sentiment_satisfied", "ac_unit",
  "chair", "auto_awesome", "star", "wb_sunny", "sell", "camping", "toggle_on",
  "train", "delete", "park", "trophy", "local_shipping", "text_fields",
  "beach_access", "person", "wallet", "watch", "wifi", "wine_bar", "build",
  "bolt",
];

/** Swatch palette the color picker offers — names are labels only; the
 * backend stores the hex itself (WColor, ADR-0005). */
export const ICON_COLORS: Record<string, string> = {
  gray: "#9e9e9e",
  red: "#e5534b",
  orange: "#e0823d",
  amber: "#d9a514",
  green: "#57ab5a",
  teal: "#39c5cf",
  blue: "#539bf5",
  purple: "#b083f0",
  pink: "#e275ad",
};

export const DEFAULT_ICON = "inventory_2";
export const DEFAULT_COLOR = "#9e9e9e";

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;

/** Stored names that predated registry validation — map them to the
 * nearest glyph that actually exists in the font. */
const ICON_ALIASES: Record<string, string> = {
  sparkles: "auto_awesome",
  puzzle: "extension",
  magnet: "attractions",
  tent: "camping",
  footprints: "podiatry",
};

/** Monochrome Material Symbols glyph for a type; unknown icon/color
 * resolve to the defaults so a stale stored value can never blank the UI. */
export function TypeIcon(props: {
  icon: string;
  color: string;
  size?: number;
}): ReactElement {
  const aliased = ICON_ALIASES[props.icon] ?? props.icon;
  const name = ICON_NAMES.includes(aliased) ? aliased : DEFAULT_ICON;
  const hex = HEX_COLOR.test(props.color) ? props.color : DEFAULT_COLOR;
  const size = props.size ?? 16;
  return (
    <span
      className="material-symbols-outlined type-icon"
      style={{ color: hex, fontSize: size, width: size, height: size }}
      aria-hidden
    >
      {name}
    </span>
  );
}
