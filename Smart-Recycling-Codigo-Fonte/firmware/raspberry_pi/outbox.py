"""Persistent HTTP outbox; successful retries keep exactly the original event ID/body."""
import json,sqlite3,time,threading,urllib.request,urllib.error,uuid
from datetime import datetime,timezone
class Outbox:
    def __init__(self,path,max_rows=1000):
        self.db=sqlite3.connect(path,check_same_thread=False);self.lock=threading.Lock();self.max_rows=max_rows
        self.db.execute('CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, body TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'pending\', next_try REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0)');self.db.commit()
    def enqueue(self,body):
        with self.lock:
            if self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]>=self.max_rows:raise RuntimeError('Outbox full; inspect pending/rejected events')
            self.db.execute('INSERT INTO outbox(id,body) VALUES(?,?)',(body['event_id'],json.dumps(body,separators=(',',':'),allow_nan=False)));self.db.commit()
    def deliver_one(self,url,key,transport=None):
        with self.lock:row=self.db.execute("SELECT id,body,attempts FROM outbox WHERE status='pending' AND next_try<=? ORDER BY rowid LIMIT 1",(time.time(),)).fetchone()
        if not row:return None
        event_id,body,attempts=row
        request=urllib.request.Request(url,data=body.encode(),headers={'Content-Type':'application/json','X-Device-Key':key},method='POST')
        try:
            with (transport or urllib.request.urlopen)(request,timeout=15) as response:status=response.status
        except urllib.error.HTTPError as error:status=error.code
        except (OSError,TimeoutError):status=0
        with self.lock:
            if status in (200,201):self.db.execute('DELETE FROM outbox WHERE id=?',(event_id,))
            elif status in (400,409,422):self.db.execute("UPDATE outbox SET status='rejected' WHERE id=?",(event_id,))
            else:self.db.execute('UPDATE outbox SET attempts=?,next_try=? WHERE id=?',(attempts+1,time.time()+min(60,2**min(attempts,6)),event_id))
            self.db.commit()
        return status
    def close(self):self.db.close()
def heartbeat(device_id,faults):
    return {'schema_version':1,'event_id':str(uuid.uuid4()),'device_id':device_id,'timestamp':datetime.now(timezone.utc).isoformat(),'type':'heartbeat','data':{'device_role':'raspberry_pi','faults':faults}}
