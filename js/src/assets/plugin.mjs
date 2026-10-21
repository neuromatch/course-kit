// {nma-data}: declares the data/image files a tutorial needs.
// nma_kit.assets (Python) turns the same declaration into the Colab/Kaggle
// download cell. The parser and URL template in both must stay in sync.

import { parseDataDirective, validateDataDirectives, assetUrlFor } from './model.mjs';

export { parseDataDirective, validateDataDirectives, assetUrlFor };

const nmaData = {
  name: 'nma-data',
  doc: 'Declare the data and image files this tutorial uses, one path per line.',
  body: { type: String, doc: 'File paths (data/..., image/...), one per line.' },
  run() {
    return [];
  },
};

export default {
  name: 'Neuromatch assets',
  directives: [nmaData],
  transforms: [],
};
