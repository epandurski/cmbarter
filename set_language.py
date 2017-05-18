#! /usr/bin/env python
from __future__ import with_statement
import sys, getopt
from cmbarter.settings import CMBARTER_DSN
from cmbarter.modules import curiousorm


USAGE = """Usage: set_language.py LANGUAGE
Set database text search language.

  -l, --list                display all supported languages
  -h, --help                display this help and exit
  --dsn=DSN                 give explicitly the database source name

Example:
  $ ./set_language.py bg
"""

LANGUAGES = """\
bg"""

def parse_args(argv):
    global dsn, language
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'hl', ['dsn=', 'help', 'list'])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)
        
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(USAGE)
            sys.exit()                  
        elif opt in ('-l', '--list'):
            print(LANGUAGES)
            sys.exit()                  
        elif opt == '--dsn':
            dsn = arg
            
    if len(args) == 1:
        language = args[0]
    else:
        print(USAGE)
        sys.exit(2)


def set_language_bg(db):
    try:
        db.execute("""
          CREATE TEXT SEARCH DICTIONARY bulgarian_ispell (
            TEMPLATE = ispell,
            DICTFILE = bulgarian,
            AFFFILE = bulgarian,
            STOPWORDS = bulgarian
          );
          """)
    except curiousorm.PgError:
        pass
    
    try:
        db.execute("""
          CREATE TEXT SEARCH CONFIGURATION public.bulgarian (
            COPY = pg_catalog.russian
          );
          """)
    except curiousorm.PgError:
        pass

    db.execute("""
      ALTER TEXT SEARCH CONFIGURATION bulgarian
        ALTER MAPPING FOR word, hword, hword_part WITH bulgarian_ispell, simple;
      """)
    db.execute("""
      ALTER DATABASE cmbarter
        SET default_text_search_config TO 'public.bulgarian';
      """)
        
        
if __name__ == "__main__":
    dsn = CMBARTER_DSN
    parse_args(sys.argv[1:])
    db = curiousorm.Connection(dsn, dictrows=True)
    try:
        if language.lower() == "bg":
            set_language_bg(db)
        else:
            print("ERROR: {} is not supported.".format(language))
    finally:
        db.close()
