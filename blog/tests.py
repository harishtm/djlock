from django.test import TransactionTestCase
from django.db import transaction
from .models import Article

DB1 = 'default'
DB2 = 'alternate'

class ArticleTestCase(TransactionTestCase):

    def setUp(self):
        self.article_id = Article.objects.create().id

    def test_publishing_twice_serial_raises_already_published(self):
        with transaction.atomic(using=DB1):
            article = Article.objects.using(DB1)
            article.get(id=self.article_id).publish()

        # The first transaction has been committed
        # before we begin the second, so the lock has been released.
        with transaction.atomic(using=DB2):
            article = Article.objects.using(DB2).get(id=self.article_id)
            with self.assertRaises(Article.AlreadyPublished):
                article.publish(DB1)

    def test_publishing_twice_parallel_raises_publishing_in_progress(self):
        with transaction.atomic(using=DB1):
            article = Article.objects.using(DB1).get(id=self.article_id)
            article.publish(DB1)

            # The first transaction has NOT been committed
            # before we begin the second, so the lock is still in effect.
            with transaction.atomic(using=DB2):
                article = Article.objects.using(DB2).get(id=self.article_id)
                with self.assertRaises(Article.PublishingInProgress):
                    article.publish(DB2)
