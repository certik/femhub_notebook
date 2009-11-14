# -*- coding: utf-8 -*-
"""
Tests to be run on the worksheet list.

AUTHORS:

- Tim Dumol (Oct. 28, 2009) -- inital version.
"""

import unittest

from sagenb.testing.notebook_test_case import NotebookTestCase

class TestWorksheetList(NotebookTestCase):
    def setUp(self):
        super(TestWorksheetList,self).setUp()
        sel = self.selenium
        self.login_as('admin', 'asdfasdf')
    
    def test_opening_worksheet(self):
        """
        Makes sure that opening a worksheet works.
        """
        sel = self.selenium
        self.create_new_worksheet('New worksheet')
        self.save_and_quit()
        sel.click("//a[@class='worksheetname']")
        sel.wait_for_page_to_load("30000")
        

    def test_creating_worksheet(self):
        """
        Tests worksheet creation.
        """
        sel = self.selenium
        self.create_new_worksheet('Creating a Worksheet')
        
        # Verify that the page has all the requisite elements.
        elements = ('link=Home', 'link=Help', 'link=Worksheet', 'link=Sign out',
                    'link=Toggle', 'link=Settings', 'link=Report a Problem',
                    'link=Log', 'link=Published', '//a[@id="worksheet_title"]',
                    '//button[@name="button_save"]')
        for element in elements:
            self.assert_(sel.is_element_present(element))

    def _search(self, phrase):
        """
        Searches for a phrase.
        """
        sel = self.selenium
        sel.type('id=search_worksheets', phrase)
        sel.click('//button[text()="Search Worksheets"]') # TODO: Fix for l18n
        sel.wait_for_page_to_load("30000")
            
    def test_searching_for_worksheets(self):
        """
        Tests search function.
        """
        sel = self.selenium

        worksheet_names = [
            'Did you just say wondeeerful?',
            'My wonderful search phrase',
            'Not a search target'
            ]

        for name in worksheet_names:
            self.create_new_worksheet(name)
            self.publish_worksheet()
            self.save_and_quit()

        pages = ('/home/admin/', '/pub', '/history')

        for page in pages:
            sel.open(page)
            self._search('wonderful')
            self.assert_(sel.is_element_present('//a[@class="worksheetname" and contains(text(), "My wonderful search phrase")]'),
                         'Search phrase not found on %s' % page)
            self.failIf(sel.is_element_present('//a[@class="worksheetname" and contains(text(), "Not a search target")]'),
                        'Non-matching search results found on %s' % page)

suite = unittest.TestLoader().loadTestsFromTestCase(TestWorksheetList)

if __name__ == '__main__':
    unittest.main()
