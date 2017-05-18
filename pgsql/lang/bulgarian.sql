CREATE TEXT SEARCH DICTIONARY bulgarian_ispell (
  TEMPLATE = ispell,
  DICTFILE = bulgarian,
  AFFFILE = bulgarian,
  STOPWORDS = bulgarian
);

CREATE TEXT SEARCH CONFIGURATION public.bulgarian (
  COPY = pg_catalog.russian
);

ALTER TEXT SEARCH CONFIGURATION bulgarian
  ALTER MAPPING FOR word, hword, hword_part WITH bulgarian_ispell, simple;
  
ALTER DATABASE cmbarter
  SET default_text_search_config TO 'public.bulgarian';
