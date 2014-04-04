import unittest
from shareclient import alfresco

# Here's our "unit tests".
class InitClientTests(unittest.TestCase):

    def testShareClient(self):

        sc = alfresco.ShareClient('http://test:8080/share')
        self.failUnless(sc.url == 'http://test:8080/share')

        sc = alfresco.ShareClient('http://test:8080/share/')
        self.failUnless(sc.url == 'http://test:8080/share')

def main():
    unittest.main()

if __name__ == '__main__':
    main()
