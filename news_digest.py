function doPost(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['Run Date', 'Article Date', 'Type', 'Title', 'Matched', 'Source', 'Link', 'Funding Related']);
  }
  
  const data = JSON.parse(e.postData.contents);
  const rows = data.rows;
  const fundingKeywords = ['raises', 'raised', 'funding', 'series a', 'series b', 'series c', 'series d', 'investment', 'invests', 'invested', 'round', 'crore', 'million', 'billion', 'expand', 'expansion', 'acquisition', 'acquires', 'acquired', 'merger', 'unicorn', 'valuation'];
  
  rows.forEach(row => {
    const text = (row.title + ' ' + row.matched).toLowerCase();
    const isFunding = fundingKeywords.some(kw => text.includes(kw)) ? 'Yes' : 'No';
    sheet.appendRow([row.run_date, row.date, row.type, row.title, row.matched, row.source, row.link, isFunding]);
  });
  
  return ContentService.createTextOutput(JSON.stringify({status: 'ok', added: rows.length}))
    .setMimeType(ContentService.MimeType.JSON);
}
