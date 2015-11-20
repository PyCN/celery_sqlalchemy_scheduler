from config import SQLALCHEMY_DATABASE_URI
from flask import Flask
from celery import Celery
from flask.ext.admin import Admin
from sqlalchemy_scheduler import dbsession
from sqlalchemy_scheduler_models import *

from flask.ext.admin.contrib.sqla import ModelView


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'],
                    backend=app.config['CELERY_RESULT_BACKEND'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


app = Flask(__name__)
app.debug = True
app.secret_key = 'super secret key'
app.config.update(
    CELERY_BROKER_URL='sqla+' + SQLALCHEMY_DATABASE_URI,
    CELERY_RESULT_BACKEND='db+' + SQLALCHEMY_DATABASE_URI,
    CELERYBEAT_SCHEDULER='sqlalchemy_scheduler.DatabaseScheduler'
)

celery = make_celery(app)
# Other admin configuration as shown in last recipe
admin = Admin(app)
admin.add_view(ModelView(CrontabSchedule, dbsession))
admin.add_view(ModelView(IntervalSchedule, dbsession))
admin.add_view(ModelView(DatabaseSchedulerEntry, dbsession))


@celery.task(name='add')
def add(x, y):
    print 'add called at ' + str(datetime.datetime.utcnow() + datetime.timedelta(hours=5))
    return x + y


@celery.task(name='multiply')
def multiply(x, y):
    print 'multiply called at ' + str(datetime.datetime.utcnow() + datetime.timedelta(hours=5))
    return x * y


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


@app.route('/schedule')
def schedule():
    dse = DatabaseSchedulerEntry()
    dse.name = 'scheduler'
    dse.task = 'add'
    dse.enabled = True
    dse.args = [3, 9]
    crontab = CrontabSchedule()
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


if __name__ == '__main__':
    app.run()
