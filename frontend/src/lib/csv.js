// Convierte filas a CSV listo para Excel: comillas escapadas y BOM para que lea bien las tildes.

function cell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(rows, columns) {
  const header = columns.map((c) => cell(c.title)).join(",");
  const lines = rows.map((row) => columns.map((c) => cell(c.value(row))).join(","));
  return "\uFEFF" + [header, ...lines].join("\r\n");
}

export function downloadText(filename, text, type = "text/csv;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
