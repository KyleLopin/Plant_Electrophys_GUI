__author__ = 'Kyle Vitautas Lopin'


class usb2(object):
    def __init__(self):
        print('init usb')
        self.core = object()
        self.core.find = find_mock()
    def core(object):
        def find(self, *args):
            print('finding')
            return 1

def find_mock():
    print('finding2')
    return 1


class core(object):
    def __init__(self):
        pass
    def find(idVendor=None, idProduct=None):
        print('wtf')
