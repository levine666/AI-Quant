/** file://  guard */
function guardFileProtocol() {
  if (location.protocol !== "file:") return true;
  const msg = "请运行 python3 AI-Quant/run.py serve 后访问";
  const el = document.getElementById("loading");
  if (el) { el.classList.remove("hidden"); el.textContent = msg; }
  return false;
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().replace(/^\uFEFF/, ""));
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    if (parts.length < headers.length) continue;
    const row = {};
    headers.forEach((h, j) => {
      const v = parts[j].trim();
      row[h] = h === "date" ? v : v === "" ? NaN : Number(v);
    });
    if (!row.date || Number.isNaN(row.close)) continue;
    rows.push(row);
  }
  return rows.sort((a, b) => a.date.localeCompare(b.date));
}
