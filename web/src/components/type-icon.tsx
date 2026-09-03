import type { ReactElement } from "react";
import {
  Activity, Airplay, AlarmClock, Anchor, Aperture, Archive, ArrowRight,
  AtSign, Award, Baby, Backpack, Badge, Banknote, BarChart3, Battery,
  Beaker, Bed, Beer, Bell, Bike, Bird, Bitcoin, Bluetooth, Sailboat,
  Bomb, Bone, Book, Bookmark, Bot, Box, Brain, Briefcase, Brush, Bug,
  Building, Bus, Cake, Calculator, Calendar, CalendarClock, CalendarDays,
  Camera, Car, Cat, Cherry, Cigarette, Clock, Cloud, Code, Coffee, Coins,
  Compass, Cpu, CreditCard, Crown, CupSoda, Database, Diamond, Dice5,
  Dog, Drum, Egg, Feather, FileText, Film, Fish, Flag, Flame, FlaskConical,
  Flower, Folder, Footprints, Gamepad2, Gem, Ghost, Gift, GlassWater,
  Glasses, Globe, Grape, Guitar, Hammer, Hash, Headphones, Heart, Home,
  IceCream, Image, Key, Lamp, Laptop, Leaf, Library, Lightbulb, Link,
  Lock, Magnet, Map, MapPin, Mic, Moon, Mountain, Music, Palette, Pen,
  Percent, Phone, Piano, Pill, Pizza, Plane, Plug, Puzzle, Rocket, Ruler,
  Scale, Scissors, Search, Shield, Shirt, ShoppingBag, ShoppingCart,
  Smile, Snowflake, Sofa, Sparkles, Star, Sun, Sword, Tag, Tent, ToggleLeft,
  Train, Trash, TreePine, Trophy, Truck, Type, Umbrella, User, Wallet,
  Wand, Watch, Wifi, Wine, Wrench, Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** Curated monochrome icon registry — every user type picks from these.
 * Names are kebab-case lucide identifiers; unknown names fall back to
 * `box`. Kept as an explicit import map (not the full lucide export) so
 * the bundle only ships what the picker shows. */
export const ICONS: Record<string, LucideIcon> = {
  "activity": Activity, "airplay": Airplay, "alarm-clock": AlarmClock,
  "anchor": Anchor, "aperture": Aperture, "archive": Archive,
  "arrow-right": ArrowRight, "at-sign": AtSign, "award": Award,
  "baby": Baby, "backpack": Backpack, "badge": Badge, "banknote": Banknote,
  "bar-chart": BarChart3, "battery": Battery, "beaker": Beaker, "bed": Bed,
  "beer": Beer, "bell": Bell, "bicycle": Bike, "bird": Bird,
  "bitcoin": Bitcoin, "bluetooth": Bluetooth, "boat": Sailboat, "bomb": Bomb,
  "bone": Bone, "book": Book, "bookmark": Bookmark, "bot": Bot, "box": Box,
  "brain": Brain, "briefcase": Briefcase, "brush": Brush, "bug": Bug,
  "building": Building, "bus": Bus, "cake": Cake, "calculator": Calculator,
  "calendar": Calendar, "calendar-clock": CalendarClock,
  "calendar-day": CalendarDays, "camera": Camera, "car": Car, "cat": Cat,
  "cherry": Cherry, "cigarette": Cigarette, "clock": Clock, "cloud": Cloud,
  "code": Code, "coffee": Coffee, "coins": Coins, "compass": Compass,
  "cpu": Cpu, "credit-card": CreditCard, "crown": Crown, "cup-soda": CupSoda,
  "database": Database, "diamond": Diamond, "dice": Dice5, "dog": Dog,
  "drum": Drum, "egg": Egg, "feather": Feather, "file-text": FileText,
  "film": Film, "fish": Fish, "flag": Flag, "flame": Flame,
  "flask": FlaskConical, "flower": Flower, "folder": Folder,
  "footprints": Footprints, "gamepad": Gamepad2, "gem": Gem, "ghost": Ghost,
  "gift": Gift, "glass-water": GlassWater, "glasses": Glasses, "globe": Globe,
  "grape": Grape, "guitar": Guitar, "hammer": Hammer, "hash": Hash,
  "headphones": Headphones, "heart": Heart, "home": Home,
  "ice-cream": IceCream, "image": Image, "key": Key, "lamp": Lamp,
  "laptop": Laptop, "leaf": Leaf, "library": Library, "lightbulb": Lightbulb,
  "link": Link, "lock": Lock, "magnet": Magnet, "map": Map, "map-pin": MapPin,
  "mic": Mic, "moon": Moon, "mountain": Mountain, "music": Music,
  "palette": Palette, "pen": Pen, "percent": Percent, "phone": Phone,
  "piano": Piano, "pill": Pill, "pizza": Pizza, "plane": Plane, "plug": Plug,
  "puzzle": Puzzle, "rocket": Rocket, "ruler": Ruler, "scale": Scale,
  "scissors": Scissors, "search": Search, "shield": Shield, "shirt": Shirt,
  "shopping-bag": ShoppingBag, "shopping-cart": ShoppingCart, "smile": Smile,
  "snowflake": Snowflake, "sofa": Sofa, "sparkles": Sparkles, "star": Star,
  "sun": Sun, "sword": Sword, "tag": Tag, "tent": Tent,
  "toggle-left": ToggleLeft, "train": Train, "trash": Trash,
  "tree": TreePine, "trophy": Trophy, "truck": Truck, "type": Type,
  "umbrella": Umbrella, "user": User, "wallet": Wallet, "wand": Wand,
  "watch": Watch, "wifi": Wifi, "wine": Wine, "wrench": Wrench, "zap": Zap,
};

export const ICON_NAMES: string[] = Object.keys(ICONS);

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

export const DEFAULT_ICON = "box";
export const DEFAULT_COLOR = "gray";

/** Monochrome lucide glyph for a type; unknown icon/color resolve to
 * the defaults so a stale stored value can never blank the UI. */
export function TypeIcon(props: {
  icon: string;
  color: string;
  size?: number;
}): ReactElement {
  const Glyph = ICONS[props.icon] ?? Box;
  const hex = ICON_COLORS[props.color] ?? ICON_COLORS[DEFAULT_COLOR];
  return (
    <Glyph
      size={props.size ?? 16}
      strokeWidth={1.75}
      style={{ color: hex, flexShrink: 0 }}
      aria-hidden
    />
  );
}
