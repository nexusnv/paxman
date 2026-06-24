/*
 * validate_quote.js – Client‑side validator for OQO JSON objects using Ajv.
 *
 * This script loads the Ajv 8 validator from a CDN and validates a given JSON
 * object against the OQO schema.  It can be used in a browser or bundled into
 * your own application.  See the demo page for an example of how to use it.
 */

// Load Ajv from a CDN (if not already loaded).  This returns a Promise that
// resolves with an Ajv instance.
function loadAjv() {
  if (window.Ajv) {
    return Promise.resolve(window.Ajv);
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/ajv@8/dist/ajv.min.js';
    script.onload = () => resolve(window.Ajv);
    script.onerror = () => reject(new Error('Failed to load Ajv')); 
    document.head.appendChild(script);
  });
}

/**
 * Validate a quote JSON object against the provided schema.
 *
 * @param {Object} quoteData The quote to validate
 * @param {Object} schemaData The JSON Schema definition
 * @returns {Promise<{valid: boolean, errors: Array}>}
 */
async function validateQuote(quoteData, schemaData) {
  const Ajv = await loadAjv();
  const ajv = new Ajv({ strict: false, allErrors: true });
  const validate = ajv.compile(schemaData);
  const valid = validate(quoteData);
  return { valid, errors: validate.errors || [] };
}

// Example usage (uncomment to test in browser console):
// fetch('open-schema/oqo.json').then(r => r.json()).then(async schema => {
//   const quote = await fetch('sample_quote.json').then(r => r.json());
//   const { valid, errors } = await validateQuote(quote, schema);
//   if (valid) {
//     console.log('Quote is valid');
//   } else {
//     console.error('Quote is invalid:', errors);
//   }
// });
