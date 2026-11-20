// Imprime informe_TP3.html a PDF con Chromium (Playwright para Node).
// Uso: node a_pdf.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.join(__dirname, 'informe_TP3.html'));
  await p.pdf({ path: path.join(__dirname, 'informe_TP3.pdf'), format: 'A4', printBackground: true,
    margin: { top: '16mm', bottom: '16mm', left: '15mm', right: '15mm' }, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:7pt;color:#777;width:100%;text-align:center">TP3 Investigación Operativa · padrón terminado en 5 · pág. <span class="pageNumber"></span>/<span class="totalPages"></span></div>' });
  await b.close();
  console.log('PDF:', path.join(__dirname, 'informe_TP3.pdf'));
})();
