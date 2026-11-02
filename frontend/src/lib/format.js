const spanish = "es";

function number(value, digits) {
  return new Intl.NumberFormat(spanish, { minimumFractionDigits: digits, maximumFractionDigits: digits })
    .format(value);
}

export function percent(value, digits = 1) {
  if (value === null || value === undefined) return "—";
  return `${number(value * 100, digits)} %`;
}

export function decimal(value, digits = 3) {
  if (value === null || value === undefined) return "—";
  return number(value, digits);
}

export function integer(value) {
  return new Intl.NumberFormat(spanish).format(value);
}

export function dateTime(iso) {
  return new Date(iso).toLocaleString(spanish, { dateStyle: "short", timeStyle: "short" });
}

export function shorten(text, max = 90) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
