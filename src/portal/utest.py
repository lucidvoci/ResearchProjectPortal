#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import unittest
from query import *

class TestQuery(unittest.TestCase):
    def test_SimpleQuery(self):
        q = Query("nuclear")
        self.assertTrue("nuclear" in q.keywords)

    def test_ComplexQueries(self): 
        q = Query('nuclear programme:fp7 country:"Czech Republic" "subprogramme":PEOPLE')
        self.assertTrue("nuclear" in q.keywords)
        self.assertEqual(q.specifications["programme"], "fp7")
        self.assertEqual(q.specifications["country"], "Czech Republic")
        self.assertEqual(q.specifications["subprogramme"], "PEOPLE")

    def test_TrickyQueries(self):
        #lex = QueryLexer()
        #print lex.tokenize('nucle\\:ar bbb')
        #par = QueryParser()
        #print par.parse('nucle\\:ar bbb')

        q = Query('coordIn\\:ar coordIn:ar nucle\\:ar bbb\\:')
        self.assertTrue("coordIn:ar" in q.keywords)
        self.assertTrue("nucle:ar" in q.keywords)
        self.assertTrue("bbb:" in q.keywords)
        self.assertEqual(q.specifications, {})

    def test_TrickyQueries2(self):
        q = Query(r'nucle\"ar country:"France"')
        self.assertTrue('nucle"ar' in q.keywords)
        self.assertEqual(q.specifications["country"], "France")

if __name__ == "__main__":
    unittest.main(verbosity=2)
