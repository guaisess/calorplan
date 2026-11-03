// Versión: 2026.11.6
// Utilidades de formularios (puras): lectura de FormData y conversión de números.

/** Envuelve las entradas de un FormData (o cualquier iterable de pares). */
export function parseEntries(entries) {
  const mapa = new Map();
  for (const [clave, valor] of entries) {
    if (!mapa.has(clave)) mapa.set(clave, []);
    mapa.get(clave).push(String(valor));
  }
  return {
    uno: (clave, defecto = "") => (mapa.has(clave) ? mapa.get(clave)[0] : defecto),
    varios: (clave) => (mapa.has(clave) ? [...mapa.get(clave)] : []),
    marcado: (clave) => mapa.has(clave),
  };
}

/** Número o null si está vacío o no es un número. */
export function numero(texto) {
  if (texto === undefined || texto === null || String(texto).trim() === "") return null;
  const n = Number(texto);
  return Number.isFinite(n) ? n : null;
}

/** Texto limpio de una lista: recorta y elimina vacíos. */
export function lista(valores) {
  return valores.map((v) => v.trim()).filter(Boolean);
}
