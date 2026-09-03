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
  "local_fire_department", "experiment", "folder", "footprints",
  "sports_esports", "redeem", "water_drop", "eyeglasses", "public", "piano",
  "handyman", "tag", "headphones", "favorite", "home", "icecream", "image",
  "key", "laptop", "eco", "local_library", "lightbulb", "link", "lock",
  "magnet", "map", "location_on", "mic", "dark_mode", "landscape",
  "palette", "edit", "percent", "call", "pill", "local_pizza", "flight",
  "power", "puzzle", "rocket_launch", "straighten", "scale", "cut", "search",
  "shield", "shopping_bag", "shopping_cart", "sentiment_satisfied", "ac_unit",
  "chair", "sparkles", "star", "wb_sunny", "sell", "tent", "toggle_on",
  "train", "delete", "park", "trophy", "local_shipping", "text_fields",
  "beach_access", "person", "wallet", "watch", "wifi", "wine_bar", "build",
  "bolt",
];

/** Palette the color swatches offer — keys are what the backend stores. */
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
export const DEFAULT_COLOR = "gray";

/** Monochrome Material Symbols glyph for a type; unknown icon/color
 * resolve to the defaults so a stale stored value can never blank the UI. */
export function TypeIcon(props: {
  icon: string;
  color: string;
  size?: number;
}): ReactElement {
  const name = ICON_NAMES.includes(props.icon) ? props.icon : DEFAULT_ICON;
  const hex = ICON_COLORS[props.color] ?? ICON_COLORS[DEFAULT_COLOR];
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
