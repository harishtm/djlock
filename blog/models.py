from django.db import models, transaction, OperationalError

# Create your models here.


"""

class Article(models.Model):
    name = models.CharField(unique=True, max_length=255)
    is_published = models.BooleanField(default=False)

    def publish(self):
        # Add the side effects of publishing here.
        # e.g. send emails, communicate with apis, etc.
        self.is_published = True
        self.save()

    def __str__(self):
        return self.name


    There is a potential problem with above code. If the publish method is called on an already published article,
    we will trigger all the side effects of publishing a second time! Let’s try to prevent that.
"""


"""

class Article(models.Model):
    name = models.CharField(unique=True, max_length=255)
    is_published = models.BooleanField(default=False)

    class AlreadyPublished(Exception):
        pass

    def publish(self):

        if self.is_published:
            raise Article.AlreadyPublished

        self._publish()

    def _publish(self):
        # Add the side effects of publishing here.
        # e.g. publish emails, communicate with apis, etc.
        self.is_published = True
        self.save()

    Is this code safe now? If we only have 1 server, then yes.
    If we have multiple nodes running the same code all connected to the same database,
    then no. What happens if two different servers get the command to publish at the same time?
    Then both servers could get the same article with is_published=False, and both proceed
    to call the _publish function.
"""

# ----------------------------------------------------------------- #
# The solution is to use select_for_update to take a database lock.
# ----------------------------------------------------------------- #






class Article(models.Model):
    is_published = models.BooleanField(default=False)

    class AlreadyPublished(Exception):
        print("Already Published")

    class PublishingInProgress(Exception):
        print("Publishing in process")

    def queryset(self, db):
        return self.__class__.objects.using(db).filter(id=self.id)

    def publish(self, db='default'):
        # Avoid taking locks when obviously not needed

        if self.is_published:
            raise Article.AlreadyPublished

        # Must be in a transaction to grab a lock
        with transaction.atomic(using=db):
            # Even though self is already this article,
            # we attempt get it again but with a lock.
            try:
                article = self.queryset(db).select_for_update().get()
            except OperationalError:
                # If we don't care about the different error states of
                # AlreadyPublished and PublishingInProgress, we can omit nowait=True
                # and this try except, instead relying on the next check.
                raise Article.PublishingInProgress

            # We have to check this again now that we have the guaranteed version
            if article.is_published:
                raise Article.AlreadyPublished

            # Only now is it safe to publish
            self._publish()

    def _publish(self):
        # Add the side effects of publishing here.
        # e.g. publish emails, communicate with apis, etc.
        self.is_published = True
        self.save()

"""

    In the code above we use database locks to force the _publish function only to be called on an article
    by one server at a time. We’re using a pattern called Double-Checked Lock Synchronization.

"""


"""
    How can we test the code above? Django’s own tests use threads and sleep for a fixed number of seconds
    to get everything in the right state. It is possible to do this without threads or sleeping,
    if we make some small modifications to our code.

    In order to test this, we have to use a database that supports transactions and locks.
    Django’s select_for_update statement is completely ignored by SQLite.
    In this example I’m using MySQL.

"""

"""
    Django’s select_for_update will release the lock when the outermost transaction it is inside gets committed.
    We will use transactions cleverly to arrange a state where locks are still held by one connection while we
    try to acquire them in another.
"""

