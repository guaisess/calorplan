// Versión: 2026.11.16
// Estilos de la tarjeta (variables de tema de Home Assistant).

export const ESTILOS_TARJETA = `
ha-card { padding: 12px 16px; }
.cabecera { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.titulo { font-size: 18px; font-weight: 500; }
.espacio { flex: 1; }
.insignia { padding: 2px 8px; border-radius: 10px; font-size: 12px; background: var(--secondary-background-color); color: var(--secondary-text-color); }
.insignia.aviso { background: var(--warning-color, #ff9800); color: #fff; }
button { cursor: pointer; border: 1px solid var(--divider-color); border-radius: 6px; padding: 4px 10px; font-size: 12px; background: var(--card-background-color); color: var(--primary-text-color); }
button:hover { border-color: var(--primary-color); }
.sala { padding: 8px 0; border-top: 1px solid var(--divider-color); }
.fila { display: flex; justify-content: space-between; gap: 8px; }
.nombre { font-weight: 500; }
.estado { font-size: 13px; color: var(--secondary-text-color); }
.sala.active .estado { color: var(--success-color, #4caf50); }
.sala.paused .estado { color: var(--warning-color, #ff9800); }
.sala.disabled { opacity: .6; }
.detalle { font-size: 12px; color: var(--secondary-text-color); margin: 2px 0 6px; }
.pista { position: relative; height: 12px; background: var(--secondary-background-color); border-radius: 3px; }
.barra { position: absolute; top: 1px; bottom: 1px; border-radius: 3px; background: var(--primary-color); opacity: .7; }
.barra.active { background: var(--success-color, #4caf50); opacity: 1; }
.barra.disabled { background: var(--disabled-text-color, #9e9e9e); opacity: .5; }
.ahora { position: absolute; top: -2px; bottom: -2px; width: 2px; background: var(--error-color, #f44336); }
.eje { position: relative; height: 14px; }
.eje span { position: absolute; transform: translateX(-50%); font-size: 10px; color: var(--secondary-text-color); }
.botones { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
.vacio, .error { padding: 12px 0; color: var(--secondary-text-color); }
.error { color: var(--error-color, #f44336); }
.editor label { display: block; margin: 8px 0 2px; font-size: 13px; }
.editor input[type=text] { width: 100%; box-sizing: border-box; padding: 6px; }
`;
