"""Debug APScheduler Job API."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def test():
    s = AsyncIOScheduler()
    s.start()
    s.add_job(lambda: None, 'interval', seconds=60, id='test')
    job = s.get_job('test')
    print('Type:', type(job.next_run_time))
    print('Value:', job.next_run_time)
    print('Has isoformat:', hasattr(job.next_run_time, 'isoformat'))
    print('Dir:', [x for x in dir(job.next_run_time) if not x.startswith('_')])
    s.shutdown()

asyncio.run(test())