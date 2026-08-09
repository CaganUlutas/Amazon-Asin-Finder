"""
Utility functions for Amazon URL parsing and manipulation.
"""
import urllib.parse
import re

def generate_price_brackets(user_min: int = 0, user_max: float = float('inf')) -> list[str]:
    """
    Dynamically generates price brackets based on the user's specified min and max prices.
    Uses finer intervals for lower prices where items are more concentrated.
    """
    # Fixed cutoff points and step sizes in cents: (cutoff, step)
    # The "FBA Arbitrage" Configuration (Optimized for $38+)
    ranges = [
        (3000, 500),      # Up to $30, $5 steps (For rare low-price scans)
        (6000, 200),      # Up to $60, $2 steps (Hyper-dense range for $38+ users)
        (10000, 400),     # Up to $100, $4 steps (Dense range)
        (20000, 1000),    # Up to $200, $10 steps (Mid-high tier)
        (50000, 5000)     # Up to $500, $50 steps (High tier)
    ]
    
    brackets = []
    current = user_min
    
    for cutoff, step in ranges:
        while current < cutoff and current < user_max:
            next_val = min(current + step, cutoff, user_max)
            brackets.append(f"{current}-{int(next_val)}")
            current = next_val
            
        if current >= user_max:
            break
            
    # If we are above 50000, or user_max is very large
    if current < user_max:
        if user_max == float('inf'):
            brackets.append(f"{current}-")
        else:
            # Step by 50000 for whatever is left
            step = 50000
            while current < user_max:
                next_val = min(current + step, user_max)
                brackets.append(f"{current}-{int(next_val)}")
                current = next_val
                
    # If the user specified an exact price (min == max)
    if not brackets and user_min == user_max and user_min > 0:
        brackets.append(f"{user_min}-{user_min}")
        
    return brackets

def split_url_by_price(url: str) -> list[str]:
    """
    Split a single Amazon search URL into multiple URLs using price brackets.
    This helps bypass Amazon's 400-result (25 page) limit by breaking down
    large result sets into smaller, manageable chunks.
    
    If the user's URL already contains a price filter (p_36), it parses the
    boundaries and only generates brackets within that user-defined range.
    """
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    
    # 1. Parse existing price filters
    user_min = 0
    user_max = float('inf')
    
    for k, v in query:
        if k == 'rh':
            for f in v.split(','):
                if f.startswith('p_36:'):
                    val = f[5:]
                    parts = val.split('-')
                    try:
                        if len(parts) == 2:
                            if parts[0]:
                                user_min = int(parts[0])
                            if parts[1]:
                                user_max = int(parts[1])
                        elif len(parts) == 1 and parts[0]:
                            user_min = int(parts[0])
                            user_max = int(parts[0])
                    except ValueError:
                        pass
        elif k == 'low-price':
            try:
                user_min = int(float(v) * 100)
            except ValueError:
                pass
        elif k == 'high-price':
            try:
                user_max = int(float(v) * 100)
            except ValueError:
                pass
                
    # Generate dynamic brackets based on the user's bounds
    brackets = generate_price_brackets(user_min, user_max)
    
    # We will build a new query string for each bracket
    split_urls = []
    
    for bracket in brackets:
        new_query = []
        has_rh = False
        
        for k, v in query:
            if k == 'rh':
                has_rh = True
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
                
        # If 'rh' wasn't in the query, add the bracket via low/high price
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
        
    # Fallback if no brackets generated (should not happen)
    if not split_urls:
        return [url]
        
    return split_urls
