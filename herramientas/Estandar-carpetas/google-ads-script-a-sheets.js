/**
 * Vuelca los datos de Google Ads en la pestaña `datos-google` de la hoja de reportes
 * del cliente. Se pega en la cuenta de Google Ads del cliente (o en el MCC) y se
 * PROGRAMA a diario.
 *
 * POR QUÉ ASÍ Y NO POR API: la Google Ads API exige un developer token que Google
 * aprueba a mano y tarda. Los Ads Scripts corren DENTRO de la cuenta y no lo necesitan.
 *
 * INSTALACIÓN (una vez por cuenta):
 *   1. Google Ads → Herramientas → Acciones masivas → Scripts → «+»
 *   2. Pegar esto. Cambiar SHEET_URL y CLIENTE de abajo.
 *   3. «Autorizar» y luego «Previsualizar» para comprobar que escribe.
 *   4. Programar: Frecuencia diaria, a las 06:00.
 *      (No antes: las cifras de Google se consolidan hasta 3 h después de medianoche.)
 *   5. La hoja tiene que estar COMPARTIDA CON EDICIÓN con el Google que autoriza el script.
 *
 * DESDE UN MCC: usar la versión de abajo (MccApp) y no repetirlo por cliente.
 */

// ─────────── CONFIGURACIÓN ───────────
var SHEET_URL = 'PEGAR_AQUI_LA_URL_DE_LA_HOJA';   // la hoja de reportes del cliente
var CLIENTE   = 'PEGAR_AQUI_EL_NOMBRE';           // igual que en la pestaña `datos` de Meta
var PESTANA   = 'datos-google';
var DIAS      = 90;    // se reescriben los últimos 90 días en cada pasada
// ─────────────────────────────────────

function main() {
  var hoja = SpreadsheetApp.openByUrl(SHEET_URL).getSheetByName(PESTANA);
  if (!hoja) throw new Error('No existe la pestaña "' + PESTANA + '". ' +
                             'Créala con anadir_hoja_google.py antes de programar esto.');

  var hasta = new Date();
  var desde = new Date(hasta.getTime() - DIAS * 24 * 60 * 60 * 1000);
  var filas = leerDatos(fmt(desde), fmt(hasta), CLIENTE);

  // Se reescribe el bloque entero en vez de ir añadiendo: Google corrige cifras de días
  // pasados (conversiones que entran tarde), así que añadir dejaría datos viejos mal.
  var ultima = hoja.getLastRow();
  if (ultima > 1) hoja.getRange(2, 1, ultima - 1, hoja.getLastColumn()).clearContent();
  if (filas.length) hoja.getRange(2, 1, filas.length, filas[0].length).setValues(filas);

  Logger.log('Escritas ' + filas.length + ' filas en ' + PESTANA);
}

/** Devuelve las filas con el MISMO orden de columnas que DATOS_G del script de Python. */
function leerDatos(desde, hasta, cliente) {
  var q = 'SELECT segments.date, campaign.name, metrics.cost_micros, metrics.impressions, ' +
          'metrics.clicks, metrics.ctr, metrics.average_cpc, metrics.conversions, ' +
          'metrics.conversions_value, metrics.search_impression_share ' +
          'FROM campaign ' +
          'WHERE segments.date BETWEEN "' + desde + '" AND "' + hasta + '" ' +
          'AND metrics.impressions > 0';

  var filas = [], it = AdsApp.search(q), ahora = new Date();
  while (it.hasNext()) {
    var r = it.next();
    var fecha = r.segments.date;                    // ya viene YYYY-MM-DD
    var camp  = r.campaign.name;
    var m     = r.metrics;
    filas.push([
      cliente + '|' + fecha + '|' + camp,           // id, para no duplicar
      fecha,
      cliente,
      camp,
      Number(m.costMicros || 0) / 1000000,          // los micros a euros
      Number(m.impressions || 0),
      Number(m.clicks || 0),
      Number(m.ctr || 0),
      Number(m.averageCpc || 0) / 1000000,
      Number(m.conversions || 0),
      Number(m.conversionsValue || 0),
      Number(m.searchImpressionShare || 0),
      Utilities.formatDate(ahora, AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd HH:mm')
    ]);
  }
  return filas;
}

function fmt(d) {
  return Utilities.formatDate(d, AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd');
}

/* ───────────────────────────────────────────────────────────────────────────
   VERSIÓN MCC — una sola instalación para todos los clientes.
   Sustituye main() por esto y rellena CUENTAS con el id de cada cuenta y su hoja.

function main() {
  var CUENTAS = [
    {id: '000-000-0000', cliente: 'Cliente 01',      url: 'URL_HOJA_Cliente 01'},
    {id: '000-000-0000', cliente: 'Cliente 13', url: 'URL_HOJA_Cliente 13'},
    {id: '000-000-0000', cliente: 'MMS',         url: 'URL_HOJA_MMS'}
  ];
  for (var i = 0; i < CUENTAS.length; i++) {
    var c = CUENTAS[i];
    var it = MccApp.accounts().withIds([c.id]).get();
    if (!it.hasNext()) { Logger.log('No encuentro la cuenta ' + c.id); continue; }
    MccApp.select(it.next());
    SHEET_URL = c.url; CLIENTE = c.cliente;
    try { main_una(); } catch (e) { Logger.log(c.cliente + ' FALLÓ: ' + e); }
  }
}
   (y renombra el main() de arriba a main_una)
   ─────────────────────────────────────────────────────────────────────────── */
