import requests, re
from bs4 import BeautifulSoup


def parse_links(content):
    pattern = r'https://\S+'
    return list(re.findall(pattern, content))

def retrieve_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        return text
