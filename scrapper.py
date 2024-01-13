import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd


class WebPageScraper:
    def __init__(self, database_name='web_pages.db'):
        self.database_name = database_name
        self.create_database()

    def create_database_connection(self):
        return sqlite3.connect(self.database_name)

    def insert_new_url(self, url):
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM PAGES WHERE URL = ?", (url,))
        existing_count = cursor.fetchone()[0]

        if existing_count == 0:
            # URL doesn't exist, proceed with the INSERT
            cursor.execute("INSERT INTO PAGES (URL, TITLE, SCRAPE, SPLIT) VALUES (?, ?, ?, ?)",
                           (url, None, False, False))

        connection.commit()
        connection.close()

    def scrape_pages(self):
        connection = self.create_database_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT * FROM PAGES')
        pages_data = cursor.fetchall()

        for page in pages_data:
            page_id, url, title, scrape_flag, split_flag = page

            if not scrape_flag:
                # If SCRAPE is False, scrape the title and update the flag
                new_title = self.fetch_title(url)

                if new_title:
                    # Update the title and SCRAPE flag in the database
                    cursor.execute("UPDATE PAGES SET TITLE = ?, SCRAPE = ? WHERE ID = ?",
                                   (new_title, True, page_id))
        connection.commit()
        connection.close()

    def split_titles(self):
        connection = self.create_database_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT * FROM PAGES')
        pages_data = cursor.fetchall()

        for page in pages_data:
            page_id, url, title, scrape_flag, split_flag = page

            if not split_flag:
                # If SPLIT is False, split the title and insert keywords
                keywords = title.split()

                cursor.execute("UPDATE PAGES SET SPLIT = ? WHERE ID = ?", (True, page_id))

                # Insert keywords into the KEYWORDS table with counts
                for keyword in keywords:
                    cursor.execute("""
                                        INSERT INTO KEYWORDS (PAGE_ID, KEYWORD, KEYWORD_COUNT)
                                        VALUES (?, ?, ?)
                                    """, (page_id, keyword, 1))

        connection.commit()
        connection.close()

    def insert_keyword_change(self, change_from, change_to):
        connection = self.create_database_connection()
        cursor = connection.cursor()

        # Insert keyword change into the CHANGES table
        cursor.execute("""
                    INSERT INTO CHANGES (CHANGE_FROM, CHANGE_TO)
                    VALUES (?, ?)
                """, (change_from, change_to))

        connection.commit()
        connection.close()

    def insert_superfluous_word(self, new_superfluous):
        connection = self.create_database_connection()
        cursor = connection.cursor()

        # Insert the new superfluous word into the SUPERFLUOUS table
        cursor.execute("""
            INSERT INTO SUPERFLUOUS (WORD)
            VALUES (?)
        """, (new_superfluous,))

        connection.commit()
        connection.close()

    def clean(self):
        connection = self.create_database_connection()
        cursor = connection.cursor()

        # Update Keywords using Changes
        cursor.execute("""
                   UPDATE KEYWORDS
                   SET KEYWORD = REPLACE(KEYWORD, C.CHANGE_FROM, C.CHANGE_TO)
                   FROM CHANGES C
                   WHERE KEYWORDS.KEYWORD LIKE '%' || C.CHANGE_FROM || '%'
               """)

        # Delete superfluous words from Keywords
        cursor.execute("""
                   DELETE FROM KEYWORDS
                   WHERE KEYWORD IN (SELECT WORD FROM SUPERFLUOUS)
               """)

        # Convert all keywords to lowercase
        cursor.execute("""
                   UPDATE KEYWORDS
                   SET KEYWORD = LOWER(KEYWORD)
               """)

        # Remove symbols and special characters from Keywords
        cursor.execute("""
            UPDATE KEYWORDS
            SET KEYWORD = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(KEYWORD,'.', ''), ',',
                        ''), '@', ''),'_', ''), '$', ''), '%', ''),'^', ''),'&', ''),'(', ''),')', ''),'-', ''),'#', '')
        """)
        cursor.execute("""
            UPDATE KEYWORDS      
            SET KEYWORD = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                KEYWORD, '+', ''), '=', ''), '{', ''), '}', ''), '[', ''), ']', ''), ':', ''), ';', ''), '<', ''), '>', ''),
                '?', ''), '!', ''), '|',''), '—', ''), '... ', '')
        """)

        # Delete rows where KEYWORD is empty
        cursor.execute("""
                  DELETE FROM KEYWORDS
                  WHERE KEYWORD = ''
              """)


        # Update keyword counts based on existing keywords in the KEYWORDS table

        # Create a temporary table to store the updated keyword counts
        cursor.execute('''
            CREATE TEMPORARY TABLE TempKeywords AS
            SELECT keyword, SUM(keyword_count) as total_count
            FROM KEYWORDS
            GROUP BY keyword
        ''')
        # Clear the original KEYWORDS table
        cursor.execute('DELETE FROM KEYWORDS')
        # Insert the updated keyword counts from the temporary table to the KEYWORDS table
        cursor.execute('''
            INSERT INTO KEYWORDS (keyword, keyword_count)
            SELECT keyword, total_count
            FROM TempKeywords
        ''')
        # Drop the temporary table
        cursor.execute('DROP TABLE TempKeywords')
        connection.commit()
        connection.close()

    def fetch_title(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.title.string if soup.title else None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def create_database(self):
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()

        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS PAGES (
                        ID INTEGER PRIMARY KEY,
                        URL TEXT,
                        TITLE TEXT,
                        SCRAPE BOOLEAN,
                        SPLIT BOOLEAN
                    )
                ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS KEYWORDS (
                ID INTEGER PRIMARY KEY,
                PAGE_ID INTEGER,
                KEYWORD TEXT,
                KEYWORD_COUNT INTEGER,
                FOREIGN KEY (PAGE_ID) REFERENCES PAGES (ID)
            )
        ''')

        cursor.execute('''
                  CREATE TABLE IF NOT EXISTS CHANGES (
                      ID INTEGER PRIMARY KEY,
                      CHANGE_FROM TEXT,
                      CHANGE_TO TEXT 
                   )
        ''')

        cursor.execute('''
                  CREATE TABLE IF NOT EXISTS SUPERFLUOUS (
                      ID INTEGER PRIMARY KEY,
                      WORD TEXT     
                  )
              ''')

        connection.commit()
        connection.close()

    def generate_keyword_report(self):
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()

        cursor.execute('''
               SELECT KEYWORD, KEYWORD_COUNT
               FROM KEYWORDS
               GROUP BY KEYWORD
               ORDER BY KEYWORD_COUNT DESC
           ''')

        keyword_data = cursor.fetchall()
        connection.close()

        df = pd.DataFrame(keyword_data, columns=['Keyword', 'Appearances'])

        return df.to_dict(orient='records')

    def get_keyword_report(self):
        return self.generate_keyword_report()

