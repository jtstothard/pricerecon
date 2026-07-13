const sourceDisplayNames: Record<string, string> = {
  'v1': 'eBay',
  'ebay': 'eBay',
  'amazon_uk': 'Amazon UK',
  'cex': 'CeX',
  'aliexpress': 'AliExpress',
  'aliexpress_sg': 'AliExpress Singapore',
  'amazon': 'Amazon',
  'amazon_de': 'Amazon Germany',
  'amazon_fr': 'Amazon France',
  'amazon_it': 'Amazon Italy',
  'amazon_es': 'Amazon Spain',
  'ccl': 'CCL',
  'aria': 'Aria',
  'box': 'Box',
  'currys': 'Currys',
  'dell_uk': 'Dell UK',
  'ebuyer': 'Ebuyer',
  'johnlewis': 'John Lewis',
  'novatech': 'Novatech',
  'overclockers': 'Overclockers',
  'scan': 'Scan',
  'shopify': 'Shopify',
  'fb_marketplace': 'Facebook Marketplace',
  'facebook_marketplace': 'Facebook Marketplace',
  'hotukdeals': 'HotUKDeals',
  'reddit_bapcsalesuk': 'Reddit BAPCSalesUK',
  'reddit_hardwareswapuk': 'Reddit HardwareSwapUK',
}

export function formatSourceName(connector: string): string {
  if (!connector) return 'Unknown source'

  // Check if we have a custom display name
  const customName = sourceDisplayNames[connector.toLowerCase()]
  if (customName) return customName

  // Auto-format snake_case to readable format
  return connector
    .split(/[_\s]+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export default sourceDisplayNames
