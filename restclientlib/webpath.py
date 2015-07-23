import posixpath


class Duplicate(Exception):

    def __init__(self, child):
        super(Exception, self).__init__()
        self.child = child

    def __str__(self):
        return ('Duplicated collection {}'
                .format(self.child.key))


class ContainerNotRegistered(Exception):

    def __init__(self, container, key):
        self.container = container
        self.key = key

    def __str__(self):
        return ('Container "{}" isn\'t registered in {}'
                .format(self.key, self.container))


class PathElement(object):

    SEP = posixpath.sep

    def __init__(self):
        super(PathElement, self).__init__()
        self._childs = {}

    def _register_child(self, child):
        if child.key in self._childs:
            raise Duplicate(child)
        self._childs[child.key] = child

    def _child(self, key):
        try:
            return self._childs[key]
        except KeyError:
            raise ContainerNotRegistered(self, key)

    def nested(self, key,
               collection=None, resource=None,
               create=True, register=True):
        """Returns nested collection with specified key."""
        try:
            return self._child(key)
        except ContainerNotRegistered:
            if create:
                return Container(self,
                                 key,
                                 collection=collection,
                                 resource=resource,
                                 register=register)
            else:
                raise

    @property
    def childs(self):
        return self._childs.keys()

    @property
    def path(self):
        """Returns full path for current resource (without slash at end)."""
        raise NotImplementedError()

    def resolve(self, path, create=False, register=False):
        if not path:
            raise ValueError('cannot resolv empty path')

        if path and path[-1] == self.SEP:
            path = path[:-1]

        elements = path.split(self.SEP)[1:]

        current = self

        while elements:
            e = elements.pop(0)
            current = current.nested(e,
                                     create=create,
                                     register=register)
            yield current


class Locator(object):

    def __init__(self, container, host=None):
        self._container = container
        self._host = host

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        self._host = host

    @property
    def container(self):
        return self._container

    @property
    def as_resource(self):
        prefix = self.host.url if self.host else ''
        return prefix + self._container.path

    @property
    def as_collection(self):
        return self.as_resource + self._container.SEP

    def __iter__(self):
        return iter(self._elements)


class RootLocator(Locator):
    @property
    def as_collection(self):
        return self.as_resource


class Root(PathElement):

    def __init__(self):
        super(Root, self).__init__()

    @property
    def path(self):
        return self.SEP

    @property
    def locator(self):
        return RootLocator(self)

    def __str__(self):
        return 'Root "{}"'.format(self.path)


class NoCollection(Exception):
    pass


class NoResource(Exception):
    pass


class Container(PathElement):

    def __init__(self,
                 root,
                 key,
                 collection=None,
                 resource=None,
                 register=True):
        super(Container, self).__init__()
        key = str(key)
        if not key:
            raise ValueError('key must be defined')
        if self.SEP in key:
            raise ValueError('key cannot contain separator {}'
                             .format(self.SEP))
        self._root = root
        self._key = key
        if register:
            self._root._register_child(self)
        self._collection = collection
        self._resource = resource

    @property
    def key(self):
        return self._key

    @property
    def root(self):
        return self._root

    def collection(self, client, default=None):
        if not self._collection and not default:
            raise NoCollection()
        collection = self._collection or default
        return collection(client, self)

    def resource(self, collection, key, state=None, default=None):
        if not self._resource and not default:
            raise NoResource()
        resource = self._resource or default
        container = self.nested(key,
                                register=False)
        return resource(collection, container, state=state)

    @property
    def path(self):
        return self.root.locator.as_collection + self.key

    @property
    def locator(self):
        return Locator(self)

    def __str__(self):
        return 'Container "{}" in {}'.format(self.key,
                                             self.root)


class Host(object):

    def _untrailed(self, url):
        if url and url[-1] == PathElement.SEP:
            return url[:-1]
        else:
            return url

    def __init__(self, url):
        if not url:
            raise ValueError('url must be defined')
        super(Host, self).__init__()
        self._url = self._untrailed(url)

    @property
    def url(self):
        return self._url

    def locator(self, path_element):
        if not isinstance(path_element, PathElement):
            raise TypeError('path_element must be PathElement')
        locator = path_element.locator
        locator.host = self
        return locator

    def __str__(self):
        return 'Host "{}"'.format(self.url)
