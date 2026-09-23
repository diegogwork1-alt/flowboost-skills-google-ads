/* ═══════════════════════════════════════════════════════════════
   PLANTILLA — copiar TODO y pegar en Google Ads.
   Cambiar SHEET_URL y CLIENTE, y nada más.
   ═══════════════════════════════════════════════════════════════ */

/**
 * Vuelca los datos de Google Ads en la pestaña `datos-google` de la hoja de reportes
 * del cliente. Se pega en la cuenta de Google Ads del cliente (o en el MCC) y se
 * PROGRAMA a diario.
 *
 * POR QUÉ ASÍ Y NO POR API (revisado 22-09-2026): el motivo viejo era que la API exigía
 * un developer token que Google aprobaba a mano. Ya no: Google los retiró el 09-09-2026.
 * Se mantiene el Ads Script por las razones buenas: corre DENTRO de la cuenta, así que no
 * hay credencial externa que caduque, no consume cuota de API y no depende del VPS.
 *
 * INSTALACIÓN (una vez por cuenta):
 *   1. Google Ads → Herramientas → Acciones masivas → Scripts → «+»
 *   2. Pegar esto. Cambiar SHEET_URL y CLIENTE de abajo.
 *   3. «Autorizar» y luego «Previsualizar» para comprobar que escribe.
 *   4. Programar: Frecuencia diaria, a las 06:00.
 *      (No antes: las cifras de Google se consolidan hasta 3 h después de medianoche.)
 *   5. La hoja tiene que estar COMPARTIDA CON EDICIÓN con el Google que autoriza el script.
 *   6. ESTACIONALIDAD: la primera pasada crea un SEGUNDO archivo («Estacionalidad — <cliente>»)
 *      y escribe su URL en el registro. Pégala en SHEET_URL_ESTACIONAL y guarda. Ese archivo es
 *      interno: NO se comparte con el cliente.
 *
 * DESDE UN MCC: usar la versión de abajo (MccApp) y no repetirlo por cliente.
 */

// ─────────── CONFIGURACIÓN ───────────
var SHEET_URL = 'PEGA_AQUI_LA_URL_DE_LA_HOJA_DEL_CLIENTE';
var CLIENTE   = 'NOMBRE_DEL_CLIENTE';
var PESTANA   = 'datos-google';
var DIAS      = 90;    // se reescriben los últimos 90 días en cada pasada

// ── ESTACIONALIDAD (añadido 22-09-2026 · archivo aparte desde el 23-09-2026) ──
// Va a UN ARCHIVO DISTINTO del reporte del cliente, por dos motivos:
//   1. El reporte lo abre el CLIENTE. Miles de filas de términos ahí son ruido.
//   2. Regenerar la hoja de reportes borra las pestañas que no son de la plantilla.
// Deja SHEET_URL_ESTACIONAL vacío la primera vez: el script crea el archivo solo y
// escribe su URL en el registro. Cópiala aquí y vuelve a guardar.
var SHEET_URL_ESTACIONAL = '';                    // ← se rellena tras la primera pasada
var PESTANA_TERMINOS = 'terminos-mes';            // término × mes: en qué mes busca la gente
var PESTANA_IS       = 'is-mes';                  // campaña × mes: qué se pierde y por qué
var MESES            = 24;   // ventana de estacionalidad. 24 deja comparar el mismo mes de 2 años
var MIN_CLICS_TERMINO = 1;   // un término sin un solo clic en el mes no dice nada de demanda
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

  // La estacionalidad va DESPUÉS y en su propio try: si falla, el reporte del cliente
  // ya está escrito y no se entera nadie. Nunca al revés.
  try { volcarTerminosPorMes(); } catch (e) { Logger.log('Términos por mes FALLÓ: ' + e); }
  try { volcarISPorMes();       } catch (e) { Logger.log('IS por mes FALLÓ: ' + e); }
}

/**
 * Devuelve el libro de ESTACIONALIDAD, creándolo la primera vez.
 * Nunca es el del reporte del cliente: son dos archivos distintos a propósito.
 */
var _libroCache = null;   // se crea UNA vez por ejecución, no una por pestaña

function libroEstacional() {
  if (_libroCache) return _libroCache;
  if (SHEET_URL_ESTACIONAL) {
    _libroCache = SpreadsheetApp.openByUrl(SHEET_URL_ESTACIONAL);
    return _libroCache;
  }

  var libro = SpreadsheetApp.create('Estacionalidad — ' + CLIENTE);
  _libroCache = libro;
  // La hoja vacía que trae por defecto estorba: se borra al crear la primera de verdad.
  Logger.log('════════════════════════════════════════════════════════════');
  Logger.log('CREADO el archivo de estacionalidad de ' + CLIENTE + '.');
  Logger.log('Pega esta URL en SHEET_URL_ESTACIONAL y guarda el script:');
  Logger.log(libro.getUrl());
  Logger.log('Si no lo haces, la próxima pasada creará OTRO archivo nuevo.');
  Logger.log('════════════════════════════════════════════════════════════');
  return libro;
}

/** Devuelve la pestaña del libro de estacionalidad, creándola con su cabecera si no existe. */
function hojaConCabecera(nombre, cabecera) {
  var libro = libroEstacional();
  var h = libro.getSheetByName(nombre);
  if (!h) {
    h = libro.insertSheet(nombre);
    h.getRange(1, 1, 1, cabecera.length).setValues([cabecera]).setFontWeight('bold');
    h.setFrozenRows(1);
    var vacia = libro.getSheetByName('Hoja 1') || libro.getSheetByName('Sheet1');
    if (vacia && libro.getSheets().length > 1) libro.deleteSheet(vacia);
  }
  return h;
}

/** Escribe filas reemplazando el bloque entero (mismo criterio que el volcado diario). */
function reescribir(hoja, filas) {
  var ultima = hoja.getLastRow();
  if (ultima > 1) hoja.getRange(2, 1, ultima - 1, hoja.getLastColumn()).clearContent();
  if (filas.length) hoja.getRange(2, 1, filas.length, filas[0].length).setValues(filas);
  return filas.length;
}

/**
 * TÉRMINOS DE BÚSQUEDA POR MES — la materia prima de la estacionalidad.
 * Lo que la gente escribió DE VERDAD en Google y acabó en un clic nuestro, mes a mes.
 * Es mejor señal que Google Trends para decidir presupuestos: es demanda de NUESTRO
 * mercado, nuestra zona y nuestra oferta, no del mercado entero.
 */
function volcarTerminosPorMes() {
  var h = hojaConCabecera(PESTANA_TERMINOS,
    ['id', 'mes', 'cliente', 'termino', 'campana',
     'impresiones', 'clics', 'coste', 'conversiones', 'actualizado']);

  var desde = fmt(restarMeses(new Date(), MESES));
  var hasta = fmt(new Date());

  var q = 'SELECT segments.month, search_term_view.search_term, campaign.name, ' +
          'metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions ' +
          'FROM search_term_view ' +
          'WHERE segments.date BETWEEN "' + desde + '" AND "' + hasta + '" ' +
          'AND metrics.clicks >= ' + MIN_CLICS_TERMINO;

  var filas = [], it = AdsApp.search(q), ahora = new Date();
  while (it.hasNext()) {
    var r = it.next();
    var mes  = r.segments.month;                  // primer día del mes, YYYY-MM-DD
    var term = r.searchTermView.searchTerm;
    var camp = r.campaign.name;
    var m    = r.metrics;
    filas.push([
      CLIENTE + '|' + mes + '|' + term + '|' + camp,
      mes,
      CLIENTE,
      term,
      camp,
      Number(m.impressions || 0),
      Number(m.clicks || 0),
      Number(m.costMicros || 0) / 1000000,
      Number(m.conversions || 0),
      Utilities.formatDate(ahora, AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd HH:mm')
    ]);
  }
  Logger.log('Escritas ' + reescribir(h, filas) + ' filas en ' + PESTANA_TERMINOS);
}

/**
 * CUOTA DE IMPRESIONES POR MES, SEPARADA POR CAUSA.
 * `datos-google` ya trae la IS total, pero no dice POR QUÉ se pierde. Y son dos problemas
 * distintos: lo que se pierde por PRESUPUESTO se compra con dinero; lo que se pierde por
 * RANKING no se compra a ningún precio — se gana con relevancia y calidad.
 * Cruzado con los términos por mes, dice en qué meses hace falta más presupuesto.
 */
function volcarISPorMes() {
  var h = hojaConCabecera(PESTANA_IS,
    ['id', 'mes', 'cliente', 'campana', 'is', 'is_perdida_presupuesto',
     'is_perdida_ranking', 'impresiones', 'clics', 'coste', 'conversiones', 'actualizado']);

  var desde = fmt(restarMeses(new Date(), MESES));
  var hasta = fmt(new Date());

  // La cuota de impresiones solo existe en Búsqueda y Shopping. En Performance Max no hay,
  // y por eso se filtra: pedirla ahí devuelve vacío y ensucia la hoja con ceros falsos.
  var q = 'SELECT segments.month, campaign.name, ' +
          'metrics.search_impression_share, ' +
          'metrics.search_budget_lost_impression_share, ' +
          'metrics.search_rank_lost_impression_share, ' +
          'metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions ' +
          'FROM campaign ' +
          'WHERE segments.date BETWEEN "' + desde + '" AND "' + hasta + '" ' +
          'AND campaign.advertising_channel_type = "SEARCH" ' +
          'AND metrics.impressions > 0';

  var filas = [], it = AdsApp.search(q), ahora = new Date();
  while (it.hasNext()) {
    var r = it.next();
    var mes  = r.segments.month;
    var camp = r.campaign.name;
    var m    = r.metrics;
    filas.push([
      CLIENTE + '|' + mes + '|' + camp,
      mes,
      CLIENTE,
      camp,
      Number(m.searchImpressionShare || 0),
      Number(m.searchBudgetLostImpressionShare || 0),
      Number(m.searchRankLostImpressionShare || 0),
      Number(m.impressions || 0),
      Number(m.clicks || 0),
      Number(m.costMicros || 0) / 1000000,
      Number(m.conversions || 0),
      Utilities.formatDate(ahora, AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd HH:mm')
    ]);
  }
  Logger.log('Escritas ' + reescribir(h, filas) + ' filas en ' + PESTANA_IS);
}

/** Resta meses a una fecha sin liarse con los días (el 31 de marzo menos 1 mes no es el 31 de febrero). */
function restarMeses(d, n) {
  var x = new Date(d.getTime());
  x.setDate(1);
  x.setMonth(x.getMonth() - n);
  return x;
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
