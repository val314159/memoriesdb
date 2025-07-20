import os, sys, psycopg
from config import PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB, DEBUG, DSN
from typing import Any, Dict, List, Optional, Union, cast
from typing import Any, Dict, List, Optional, Tuple, Union

from psycopg.rows import dict_row
import numpy.typing as npt
import uuid
from config import OLLAMA_URL, EMBEDDING_MODEL, CHAT_MODEL

from db_ll_utils import get_current_user_id

from logging_setup import get_logger
logger = get_logger(__name__)

# Build Database Connection String
#logger.info("Database connection configured with DSN:  sync " +
#            DSN.replace(PG_PASS, "***") if PG_PASS else DSN)
