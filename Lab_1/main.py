import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sqlite3

# сслыки неприятные, поэтому приходится как-то обходить

site_url = 'https://ngs24.ru'
page_url = lambda num_url: f'{site_url}/text/?page={num_url}'

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:123.0) Gecko/20100101 Firefox/123.0'}


def table_add_db(conn):
    try:
        cur = conn.cursor()
        cur.execute('''create table if not exists test
                          (id integer primary key autoincrement,
                          title text,
                          body text,
                          category text,
                          created_date text)''')
        conn.commit()
    except sqlite3.Error as x:
        print('Ошибка создания таблицы:', x)


def insert_table_db(conn, title, body, category, created_datetime):
    try:
        cur = conn.cursor()
        cur.execute('''INSERT INTO test (title, body, category, created_date) VALUES (?, ?, ?, ?)''', (title, "\n".join(body), category, created_datetime))
        conn.commit()
    except sqlite3.Error as e:
        print('Ошибка добавления: ', e)


def save_to_db(title, body, category, created_datetime):
    conn = sqlite3.connect('test.db')
    table_add_db(conn)
    insert_table_db(conn, title, body, category, created_datetime)
    conn.close()


async def fetch_content(url, session):
    async with session.get(url, headers=headers) as response:
        return await response.text()


async def get_page_urls(session):
    async with session.get(site_url+'/text', headers=headers) as response:
        if response.status == 200:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            pagination = soup.find(attrs={'data-test': 'pagination-component'}) # через классы искать неудобно, проще через объявленные атрибуты тэгов
            cleaned_text = pagination.text.split('...')
            pages = list(map(int, cleaned_text)) # костыльное решение пагинации
            if pages[0] > 1:
                pages[0] = 1
            min_page = min(pages)
            max_page = max(pages)
            return [page_url(page_number) for page_number in range(min_page, max_page + 1)]
        else:
            print('Ошибка при запросе:', response.status)
            return []


async def get_article_urls(url, session):
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.find_all(attrs={'data-test': 'archive-record-item'})
            lst = []
            lst = [item.find('a').get('href') for item in content]
            print(lst)
            for i, x in enumerate(lst): # ссылки имеют вид  "/text/...", однако рекламные и опросники именно с доступом через домен, а не внутренюю логику сервера
                while True:
                    if len(lst) > i:
                        if 'https' in lst[i]:
                            lst.pop(i) # тут можно поставить break point для дебага и увидеть, как они различаются 
                        else:
                            break
                    else:
                        break
            print(lst) # проверка списка ссылок в начале и в конце, после обработки
            return lst
        else:
            print('Ошибка при запросе:', response.status)
            return []


async def get_article_content(url, session):
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.find('h1').text
            body = [p.text for p in soup.find('main').find_all('p')]
            category = soup.find(attrs={'name': 'articleHeader'}).find('meta').get('content') # доступ к категории есть через мета-тэги, там как раз достается этот тэг
            datetime = soup.find('time').text
            return title, body, category, datetime
        else:
            print('Ошибка при запросе:', response.status)
            return None, None, None, None


async def main():
    conn = sqlite3.connect('test.db')
    async with aiohttp.ClientSession(trust_env=True) as session:
        page_urls = await get_page_urls(session)
        for page_url in page_urls:
            print(f'\n\n{page_url}\n')
            article_urls = await get_article_urls(page_url, session)
            for article_url in article_urls:
                title, body, category, datetime = await get_article_content(site_url + article_url, session)
                if title and body and category and datetime:
                    print(title)
                    #save_to_db(title, body, category, datetime)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
