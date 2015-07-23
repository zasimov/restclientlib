import os
import sys

from restclientlib import webpath
from restclientlib import client


# Disable insecure platform warning
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


class Article(client.Resource):
    @property
    def translations(self):
        for definition in self._state['def']:
            for translation in definition['tr']:
                yield translation['text']


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--help':
        print 'usage: yandex-translate.py word1 word2 ...'
        exit(0)

    try:
        KEY = os.environ['YANDEX_API_KEY']
    except KeyError:
        print 'Please set YANDEX_API_KEY environment variable'
        exit(1)

    host = webpath.Host('https://dictionary.yandex.net')

    dictservice = client.Client(host)

    article = (dictservice
               .collection("api")
               .collection("v1")
               .collection("dicservice.json")
               .resource("lookup",
                         resource=Article))

    for text in sys.argv[1:]:
        article.fetch(params={'key': KEY,
                              'lang': 'en-ru',
                              'text': text})


        print 'Translations for "{}":'.format(text)
        for translation in article.translations:
            print ' '*8, translation.encode('utf-8')
        print
