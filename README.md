# What is the project about ?

This repo contains my modification of the Celery Database Scheduler from
djcelery project. I've used it in production for over a year now without
problems.
Moreover, you can this with non-django project like flask. Please see the examples below


## How do I use this

You'll have to include the scheduler module in your project and modify the
models to work with your SQLAlchemy setup. The code in repo just uses temporary
in-memory SQLite database since I cannot assume anything.

Finally, set `CELERYBEAT_SCHEDULER` to
`yourproject.sqlalchemy_scheduler:DatabaseScheduler`.

Adding and removing tasks is done with manipulating the SQLAlchemy models.

```python
dse = model.DatabaseSchedulerEntry()
dse.name = 'Simple add task'
dse.task = 'yourproject.tasks.add'
dse.arguments = '[]'  # json string
dse.keyword_arguments = '{}'  # json string

# crontab defaults to run every minute
dse.crontab = model.CrontabSchedule()

dbsession.add(dse)
dbsession.commit()
```
## Tutorial
Below is the quick tutorial to run this project with flask successfully

### Create db models

First of all create our db models. There are three model classes

1. CrontabSchedule
2. IntervalSchedule
3. DatabaseSchedulerEntry


### Our Simple Celery Tasks


**Add task**
```
@celery.task(name='add')
def add(x, y):
    print 'add called at ' + str(datetime.datetime.utcnow() + datetime.timedelta(hours=5))
    return x + y
```

**Multiply task**

```
@celery.task(name='multiply')
def multiply(x, y):
    print 'multiply called at ' + str(datetime.datetime.utcnow() + datetime.timedelta(hours=5))
    return x * y
```

### Schedule Task

```
@app.route('/schedule')
def schedule():
    dse = DatabaseSchedulerEntry()
    dse.name = 'scheduler'
    #name of task to run
    dse.task = 'add'
    dse.enabled = True
    #arguments to pass to our task function
    dse.args = [3, 9]
    crontab = CrontabSchedule()
    #set the time to call our task function
    dtime = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
    crontab.day_of_month = dtime.day
    crontab.hour = dtime.hour
    crontab.minute = dtime.minute
    crontab.month_of_year = dtime.month
    dse.crontab = crontab
    dbsession.add(crontab)
    dbsession.add(dse)
    dbsession.commit()
    return 'Task is scheduled at %s' % dtime
```


### Schedule Periodic Task


Now suppose you want to add periodic task on some time and it runs with frequency like daily, weekly, hourly, minutely, secondly

```
@app.route('/periodic')
def periodic():
    dse = DatabaseSchedulerEntry()
    dse.name = 'scheduler'
    dse.task = 'PeriodicTask'
    dse.enabled = True

    # schudule task to run after 30 seconds
    dtime = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

    #interval
    period = 8
    frequency = 'seconds'

    crontab = CrontabSchedule()
    crontab.day_of_month = dtime.day
    crontab.hour = dtime.hour
    crontab.minute = dtime.minute
    crontab.month_of_year = dtime.month
    dse.args = [2, 8]
    dse.kwargs = dict(period=period,
                      frequency=frequency,
                      taskname='multiply')
    dse.crontab = crontab

    #add entry to db
    dbsession.add(crontab)
    dbsession.add(dse)
    dbsession.commit()
    return 'Task successfully scheduled to run on %s with frequency period of %d seconds' % \
           (dtime, period)
```

The periodic task method which schedule interval tasks

```
@celery.task(name='PeriodicTask')
def schedule_periodic_task(*args, **kwargs):
    dse = DatabaseSchedulerEntry()
    dse.name = 'scheduler'
    dse.task = kwargs['taskname']
    dse.args = args
    interval = IntervalSchedule()
    interval.period = kwargs['frequency']
    interval.every = kwargs['period']
    dse.interval = interval
    dbsession.add(interval)
    dbsession.add(dse)
    dbsession.commit()
    return 'Interval task Scheduled'
```


###Running Celery Worker


Here is the command to run celery worker


`celery -A app.celery worker --loglevel=info`

And to run beat with our scheduler


`celery -A app.celery beat -S sqlalchemy_scheduler:DatabaseScheduler`

where app is the file name and celery is the object inside the app

I have add example project which shows tasks status in form of flask admin UI.
