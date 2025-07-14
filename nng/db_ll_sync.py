import os, sys, psycopg
from config import PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB, DEBUG, DSN
from logging_setup import get_logger

logger = get_logger(__name__)

# Build Database Connection String
logger.info("Database connection configured with DSN:  sync " +
            DSN.replace(PG_PASS, "***") if PG_PASS else DSN)

