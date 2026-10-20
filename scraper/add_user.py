import sys

from scraper.scraper import Scraper

username = sys.argv[1]

scraper = Scraper()
scraper.integrate_user(username, add_friends=False)
scraper.conn.close()