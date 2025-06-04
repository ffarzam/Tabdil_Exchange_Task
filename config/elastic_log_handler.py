import json
import logging
import time
from datetime import datetime

from elasticsearch import Elasticsearch


class ElasticsearchHandler(logging.Handler):
    def __init__(self, host, port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.es = Elasticsearch(f'http://{host}:{port}')

    def emit(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'level': record.levelname,
        }
        log_entry.update(json.loads(self.format(record)))

        self.es.index(index=self.get_index_name(), document=log_entry)

    @staticmethod
    def get_index_name():
        return f'log_{time.strftime("%Y_%m_%d")}'
