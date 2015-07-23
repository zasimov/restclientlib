import json

import requests

import codes
import exceptions
import webpath


class AbstractTransport(object):

    def get(self, url, params, headers):
        raise NotImplementedError()

    def post(self, url, data, params, headers):
        raise NotImplementedError()

    def put(self, url, data, params, headers):
        raise NotImplementedError()

    def delete(self, url, params, headers):
        raise NotImplementedError()


class AbstractSerializer(object):
    def serialize(self, data):
        raise NotImplementedError()

    def unserialize(self, response):
        raise NotImplementedError()


class Handler(object):
    def __init__(self, host, container, transport, serializer):
        super(Handler, self).__init__()
        self._host = host
        self._container = container
        self._transport = transport
        self._serializer = serializer

    @property
    def host(self):
        return self._host

    @property
    def container(self):
        return self._container

    @property
    def url(self):
        return self.host.locator(self.container).as_collection

    @property
    def transport(self):
        return self._transport

    @property
    def serializer(self):
        return self._serializer

    def _handle_error(self, response):
        raise exceptions.ClientException(
            response.status_code,
            response.reason,
            response.content)

    def execute(self):
        raise NotImplementedError()


class CreateHandler(Handler):

    def __init__(self, host, container, data,
                 params, headers,
                 transport, serializer):
        super(CreateHandler, self).__init__(host,
                                            container,
                                            transport,
                                            serializer)
        self._data = data
        self._params = params
        self._headers = headers.copy() if headers else {}

    def execute(self):
        response = self.transport.post(
            self.url,
            data=self.serializer.serialize(self._data),
            params=self._params,
            headers=self._headers)
        if response.status_code == codes.CREATED:
            return self.serializer.unserialize(
                response.content)
        else:
            return self._handle_error(response)


class PutHandler(Handler):

    @property
    def url(self):
        return self.host.locator(self.container).as_resource

    def __init__(self, host, container, data,
                 params, headers,
                 transport, serializer):
        super(PutHandler, self).__init__(host,
                                         container,
                                         transport,
                                         serializer)
        self._data = data
        self._params = params
        self._headers = headers.copy() if headers else {}

    def execute(self):
        response = self.transport.put(
            self.url,
            data=self.serializer.serialize(self._data),
            params=self._params,
            headers=self._headers)
        if response.status_code == codes.OK:
            return self.serializer.unserialize(
                response.content)
        else:
            return self._handle_error(response)


class ListHandler(Handler):

    def __init__(self, host, container,
                 params, headers,
                 transport, serializer):
        super(ListHandler, self).__init__(host,
                                         container,
                                         transport,
                                         serializer)
        self._params = params
        self._headers = headers.copy() if headers else {}

    def execute(self):
        response = self.transport.get(
            self.url,
            params=self._params,
            headers=self._headers)
        if response.status_code == codes.OK:
            return self.serializer.unserialize(
                response.content)
        else:
            return self._handle_error(response)


class GetHandler(ListHandler):

    @property
    def url(self):
        return self.host.locator(self.container).as_resource


class DeleteHandler(Handler):

    @property
    def url(self):
        return self.host.locator(self.container).as_resource

    def __init__(self, host, container,
                 params, headers,
                 transport, serializer):
        super(DeleteHandler, self).__init__(host,
                                         container,
                                         transport,
                                         serializer)
        self._params = params
        self._headers = headers.copy() if headers else {}

    def execute(self):
        response = self.transport.delete(
            self.url,
            params=self._params,
            headers=self._headers)
        if response.status_code == codes.NO_CONTENT:
            return
        else:
            return self._handle_error(response)


class RequestsTransport(AbstractTransport):

    def get(self, url, params, headers):
        return requests.get(url,
                            params=params,
                            headers=headers)

    def post(self, url, data, params, headers):
        return requests.post(url,
                             data=data,
                             params=params,
                             headers=headers)

    def put(self, url, data, params, headers):
        return requests.put(url,
                            data=data,
                            params=params,
                            headers=headers)

    def delete(self, url, params, headers):
        return requests.delete(url,
                               params=params,
                               headers=headers)


class JsonSerializer(AbstractSerializer):

    def serialize(self, data):
        return json.dumps(data)

    def unserialize(self, raw):
        return json.loads(raw)


class Controller(object):

    def __init__(self, client, container):
        if not isinstance(client, Client):
            raise TypeError('client must be Client')
        super(Controller, self).__init__()
        self._client = client
        self._container = container

    @property
    def client(self):
        return self._client

    @property
    def transport(self):
        return self.client.transport

    @property
    def serializer(self):
        return self.client.serializer

    @property
    def host(self):
        return self.client.host

    @property
    def container(self):
        return self._container


class Collection(Controller):

    def __init__(self, parent, container):
        if not isinstance(container, webpath.Container):
            raise TypeError('container must be Container')
        if isinstance(parent, Client):
            client = parent
        else:
            client = parent.client
        super(Collection, self).__init__(client, container)
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    def _keyfunc(self, state):
        return state['uuid']

    def _create_handler(self, *args):
        return CreateHandler(*args)

    def _list_handler(self, *args):
        return ListHandler(*args)

    def create(self, data,
               params=None,
               headers=None,
               keyfunc=None,
               resource=None):
        handler = self._create_handler(
            self.host,
            self.container,
            data,
            params,
            headers,
            self.transport,
            self.serializer)
        state = handler.execute()
        # FIXME(Alexey Zasimov): How to detect key?
        keyfunc = keyfunc or self._keyfunc
        key = keyfunc(state)
        resource = resource or FastResource
        return self.container.resource(self, key, state=state,
                                       default=resource)

    def list(self,
             params=None,
             headers=None,
             keyfunc=None,
             resource=None):
        handler = self._list_handler(
            self.host,
            self.container,
            params,
            headers,
            self.transport,
            self.serializer)
        keyfunc = keyfunc or self._keyfunc
        resource = resource or FastResource
        return map(
            lambda state: self.container.resource(self,
                                                  keyfunc(state),
                                                  state,
                                                  default=resource),
            handler.execute())

    def collection(self, key):
        container = self.container.nested(key)
        return container.collection(self,
                                    default=Collection)

    def resource(self, key, resource=None):
        resource = resource or FastResource
        return self.container.resource(self,
                                       key,
                                       default=resource)


class Resource(Controller):

    def __init__(self, parent, container, state=None):
        super(Resource, self).__init__(parent.client,
                                       container)
        self._parent = parent
        self._state = state

    @property
    def key(self):
        return self.container.key

    @property
    def parent(self):
        return self._parent

    def lift(self, state):
        self._state = state

    def unlift(self):
        return self._state

    def _get_handler(self, *args):
        return GetHandler(*args)

    def _put_handler(self, *args):
        return PutHandler(*args)

    def _delete_handler(self, *args):
        return DeleteHandler(*args)

    def fetch(self, params=None, headers=None, refresh=False):
        if refresh or not self._state:
            handler = self._get_handler(
                self.host,
                self.container,
                params,
                headers,
                self.transport,
                self.serializer)
            self._state = handler.execute()
        return self._state

    def update(self, state, params=None, headers=None):
        handler = self._put_handler(
            self.host,
            self.container,
            state,
            params,
            headers,
            self.transport,
            self.serializer)
        state = handler.execute()
        # FIXME(Alexey Zasimov): How to detect key?
        self._state = state
        return state

    def delete(self, params=None, headers=None):
        handler = self._delete_handler(
            self.host,
            self.container,
            params,
            headers,
            self.transport,
            self.serializer)
        return handler.execute()

    def collection(self, key):
        container = self.container.nested(key)
        return container.collection(self,
                                    default=Collection)


class FastResource(Resource):
    def __getattr__(self, attr):
        self.fetch()
        try:
            return self._state[attr]
        except KeyError:
            raise AttributeError


class Client(object):

    def __init__(self, host, root=None):
        super(Client, self).__init__()
        self._host = host
        self._root = root or webpath.Root()
        self._transport = RequestsTransport()
        self._serializer = JsonSerializer()

    @property
    def host(self):
        return self._host

    @property
    def root(self):
        return self._root

    @property
    def parent(self):
        return None

    @property
    def transport(self):
        return self._transport

    @property
    def serializer(self):
        return self._serializer

    def collection(self, key):
        container = self.root.nested(key)
        return container.collection(self,
                                    default=Collection)

    def resolve(self, url):
        containers = list(self.root.resolve(url))
        top = containers.pop(0)
        current = self.collection(top.key)
        while containers:
            container = containers.pop(0)
            try:
                if isinstance(current, Collection):
                    current = current.resource(container.key)
                else:
                    current = current.collection(container.key)
            except webpath.NotResource:
                current = current.collection(container.key)
        return current
