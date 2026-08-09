"""
Utility functions for Amazon URL parsing and manipulation.
"""
import urllib.parse

# Price brackets in cents for Smart Crawl
PRICE_BRACKETS = [
    "0-500",        # $0 - $5
    "500-1000",     # $5 - $10
    "1000-1500",    # $10 - $15
    "1500-2000",    # $15 - $20
    "2000-2500",    # $20 - $25
    "2500-3000",    # $25 - $30
    "3000-3500",    # $30 - $35
    "3500-4000",    # $35 - $40
    "4000-4500",    # $40 - $45
    "4500-5000",    # $45 - $50
    "5000-6000",    # $50 - $60
    "6000-7000",    # $60 - $70
    "7000-8000",    # $70 - $80
    "8000-10000",   # $80 - $100
    "10000-15000",  # $100 - $150
    "15000-20000",  # $150 - $200
    "20000-50000",  # $200 - $500
    "50000-",       # $500+
]

def split_url_by_price(url: str) -> list[str]:
    """
    Split a single Amazon search URL into multiple URLs using price brackets.
    This helps bypass Amazon's 400-result (25 page) limit by breaking down
    large result sets into smaller, manageable chunks.
    
    Args:
        url: The original Amazon search URL
        
    Returns:
        List of modified URLs with price filters applied
    """
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    
    # We will build a new query string for each bracket
    split_urls = []
    
    for bracket in PRICE_BRACKETS:
        new_query = []
        for k, v in query:
            if k == 'rh':
                # Split existing filters by comma
                filters = v.split(',')
                # Remove any existing p_36 (price) filters
                filters = [f for f in filters if not f.startswith('p_36:')]
                # Append our new price bracket
                filters.append(f'p_36:{bracket}')
                # Rejoin
                new_query.append((k, ','.join(filters)))
            elif k in ('low-price', 'high-price'):
                # Strip these out to avoid conflicts
                continue
            else:
                new_query.append((k, v))
                
        # If 'rh' wasn't in the query, we should add it? 
        # Usually Amazon URLs always have rh or it's a basic search.
        # If it doesn't have rh, we can just add low-price and high-price
        has_rh = any(k == 'rh' for k, _ in new_query)
        if not has_rh:
            if "-" in bracket:
                low, high = bracket.split("-")
                if low:
                    new_query.append(('low-price', str(int(low) / 100)))
                if high:
                    new_query.append(('high-price', str(int(high) / 100)))
        
        # Build the new URL
        new_encoded_query = urllib.parse.urlencode(new_query)
        new_url = urllib.parse.urlunparse(parsed._replace(query=new_encoded_query))
        split_urls.append(new_url)
        
    return split_urls
