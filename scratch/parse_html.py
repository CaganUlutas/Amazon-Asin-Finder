from bs4 import BeautifulSoup
import re

with open('scratch/automotive.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

pagination = soup.select_one('.s-pagination-strip')
if pagination:
    print("Pagination strip text:")
    print(pagination.text.strip().replace('\n', ' '))
    
    items = pagination.select(".s-pagination-item:not(.s-pagination-next):not(.s-pagination-previous):not(.s-pagination-ellipsis)")
    for item in items:
        print(f"Page item: {item.text.strip()}")
else:
    print("No pagination strip found")
