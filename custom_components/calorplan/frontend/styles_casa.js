// Versión: 2026.11.6
// Estilos de la vista «Casa» (formularios, diálogos).

export const ESTILOS_CASA = `
.vistas { margin-bottom: 16px; }
.titulo-tarjeta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.titulo-tarjeta h2 { margin: 0; }
h3 { margin: 18px 0 8px; font-size: 14px; font-weight: 500; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
form { max-width: 760px; }
.campo { display: block; margin: 10px 0; }
.campo > span { display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px; }
input, select, textarea { width: 100%; box-sizing: border-box; padding: 8px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--secondary-background-color); color: var(--primary-text-color); font: inherit; }
input[readonly] { opacity: .7; }
input[type="checkbox"], input[type="radio"] { width: auto; }
.fila { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.fila input { flex: 1; }
.fila .id-canal { flex: 0 0 160px; }
.fila button { flex: 0 0 auto; }
.casilla { display: flex; align-items: center; gap: 8px; margin: 8px 0; }
.casillas { display: flex; flex-wrap: wrap; gap: 4px 16px; }
button.primario { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
button:disabled { opacity: .5; cursor: not-allowed; }
.botones { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.validacion { margin-top: 12px; padding: 8px 0; font-size: 13px; }
.avisos { margin: 4px 0 0; padding-left: 20px; color: var(--warning-color, #ff9800); font-size: 13px; }
.acciones { white-space: nowrap; text-align: right; }
.tramo-off td { opacity: .6; }
.acciones button { margin-left: 4px; }
.modal-fondo { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: flex-start; justify-content: center; padding: 32px 16px; overflow-y: auto; z-index: 10; }
.modal { background: var(--card-background-color); border-radius: 12px; padding: 20px; width: 100%; max-width: 640px; box-shadow: 0 8px 30px rgba(0,0,0,.5); }
.modal h2 { margin: 0 0 8px; font-size: 18px; font-weight: 500; }
code { background: var(--secondary-background-color); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
`;
