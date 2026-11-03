// Versión: 2026.11.5
// Estilos del panel (usa las variables de tema de Home Assistant).

export const ESTILOS = `
:host { display: block; padding: 16px; color: var(--primary-text-color); background: var(--primary-background-color); min-height: 100%; box-sizing: border-box; }
.cabecera { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.cabecera h1 { margin: 0; font-size: 24px; font-weight: 400; }
.insignia { padding: 2px 10px; border-radius: 12px; font-size: 12px; background: var(--secondary-background-color); color: var(--secondary-text-color); }
.insignia.aviso { background: var(--warning-color, #ff9800); color: #fff; }
.espacio { flex: 1; }
button { cursor: pointer; border: 1px solid var(--divider-color); border-radius: 6px; padding: 6px 12px; background: var(--card-background-color); color: var(--primary-text-color); }
button:hover { border-color: var(--primary-color); }
.tarjeta { background: var(--card-background-color); border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.2)); }
.tarjeta h2 { margin: 0 0 12px; font-size: 16px; font-weight: 500; }
.pestanas { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.pestanas button.sel { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
.pestanas button.hoy::after { content: " •"; }
.gantt { display: grid; grid-template-columns: 150px 1fr; row-gap: 6px; align-items: center; }
.etiqueta { font-size: 13px; padding-right: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.etiqueta small { display: block; color: var(--secondary-text-color); font-size: 11px; }
.eje { position: relative; height: 18px; border-bottom: 1px solid var(--divider-color); }
.eje span { position: absolute; transform: translateX(-50%); font-size: 11px; color: var(--secondary-text-color); }
.pista { position: relative; height: 26px; background: var(--secondary-background-color); border-radius: 4px; }
.marca { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--divider-color); }
.barra { position: absolute; top: 3px; bottom: 3px; border-radius: 4px; background: var(--primary-color); opacity: .75; font-size: 11px; color: var(--text-primary-color, #fff); overflow: hidden; white-space: nowrap; padding: 0 4px; line-height: 20px; box-sizing: border-box; }
.barra.active { opacity: 1; background: var(--success-color, #4caf50); }
.barra.disabled { background: var(--disabled-text-color, #9e9e9e); opacity: .5; }
.barra.cont-izq { border-top-left-radius: 0; border-bottom-left-radius: 0; }
.barra.cont-der { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.ahora { position: absolute; top: -2px; bottom: -2px; width: 2px; background: var(--error-color, #f44336); z-index: 2; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--secondary-text-color); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--divider-color); }
td { padding: 8px; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
.ok { color: var(--success-color, #4caf50); }
.warn { color: var(--warning-color, #ff9800); }
.error { color: var(--error-color, #f44336); }
.muted { color: var(--secondary-text-color); }
.mensaje { padding: 24px; text-align: center; color: var(--secondary-text-color); }
`;
