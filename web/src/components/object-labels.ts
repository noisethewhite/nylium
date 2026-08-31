import type { ObjectView } from "../contracts";
import { PropValues } from "../contracts";

/** Display labels for objects — in lists, ref pickers, headers.
 * First non-null scalar prop wins; uuid tail is the fallback. */
export abstract class ObjectLabels {
  private static readonly UUID_TAIL = 8;

  static of(view: ObjectView): string {
    for (const value of Object.values(view.props)) {
      if (PropValues.isScalar(value) && value.value !== null && value.value !== "") {
        return String(value.value);
      }
    }
    return view.uuid.slice(0, ObjectLabels.UUID_TAIL);
  }

  static shortUuid(view: ObjectView): string {
    return view.uuid.slice(0, ObjectLabels.UUID_TAIL);
  }
}
