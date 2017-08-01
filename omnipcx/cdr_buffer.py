import os, os.path, sqlite3, queue
from omnipcx.logging import Loggable
from omnipcx.messages.protocol import SMDR

class CDRBuffer(Loggable):
    def __init__(self, file):
        super(CDRBuffer, self).__init__()
        self.queue = queue.LifoQueue()
        self.db_file = file

    def put(self, message):
        self.queue.put(message, False)

    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None

    @property
    def is_empty(self):
        return self.queue.empty()

    def load(self):
        if not os.path.exists(self.db_file):
            return self.logger.warn("CDR buffer database doesn't exist. No need to load!")
        self.logger.info("Loading buffer from database")
        db_conn = sqlite3.connect(self.db_file)
        cursor = db_conn.cursor()
        for row in cursor.execute("SELECT * FROM cdr"):
            self.logger.debug("Loading message : '%s'" % row[0])
            self.queue.put(SMDR(row[0], with_ends=False))

    def save(self):
        try:
            os.remove(self.db_file)
        except OSError:
            pass
        if self.is_empty:
            return self.logger.warn("CDR buffer is empty. No need to save!")
        db_conn = sqlite3.connect(self.db_file)
        cursor = db_conn.cursor()
        self.logger.debug("Creating buffer database")
        cursor.execute('CREATE TABLE cdr(payload text)')
        self.logger.info("Saving buffered CDRs to database")
        payloads=[]
        while True:
            item = self.get()
            if item is None:
                break
            payloads.insert(0, (item.payload,))
        cursor.executemany('INSERT INTO cdr VALUES(?)', payloads)
        db_conn.commit()
        db_conn.close()




